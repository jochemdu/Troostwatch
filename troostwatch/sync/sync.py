"""Synchronization module for fetching and persisting auction data."""

from __future__ import annotations

from dataclasses import dataclass, asdict
import asyncio
import hashlib
import html
import json
import re
import time
from typing import Iterable, List, Optional, Tuple, Dict
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from ..db import ensure_core_schema, ensure_schema, get_connection, iso_utcnow
from ..http_client import TroostwatchHttpClient
from ..parsers.lot_card import (
    LotCardData,
    extract_page_urls,
    parse_auction_page,
    parse_lot_card,
)
from ..parsers.lot_detail import LotDetailData, parse_lot_detail
from .fetcher import HttpFetcher, RequestResult


@dataclass
class PageResult:
    url: str
    html: str


@dataclass
class SyncRunResult:
    run_id: int | None
    status: str
    pages_scanned: int
    lots_scanned: int
    lots_updated: int
    error_count: int
    errors: list[str]


def _log(message: str, verbose: bool) -> None:
    if not verbose:
        return
    try:
        import click

        click.echo(message)
    except ImportError:
        print(message)


def _fetch_url(
    url: str, http_client: TroostwatchHttpClient | None = None
) -> Tuple[Optional[str], Optional[str]]:
    """Fetch the contents of a URL and return HTML plus any error message."""

    try:
        if http_client is not None:
            response_text = http_client.fetch_text(url)
            return response_text, None

        req = Request(url, headers={"User-Agent": "troostwatch-sync/0.1"})
        with urlopen(req) as response:
            data = response.read()
            try:
                return data.decode("utf-8"), None
            except UnicodeDecodeError:
                return data.decode("latin1"), None
    except (HTTPError, URLError) as exc:
        return None, str(exc)
    except Exception as exc:  # pragma: no cover - safety net
        return None, str(exc)


def _extract_page_urls(html_text: str, base_url: str) -> List[str]:
    urls: List[str] = []
    for match in re.finditer(
        r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>\s*(\d+)\s*</a>',
        html_text,
        re.IGNORECASE,
    ):
        link = match.group(1)
        if link.startswith("javascript") or link.startswith("mailto"):
            continue
        if link.startswith("/"):
            full_url = base_url.rstrip("/") + link
        elif link.startswith("http://") or link.startswith("https://"):
            full_url = link
        else:
            if base_url.endswith("/"):
                full_url = base_url + link
            else:
                full_url = base_url + "/" + link
        if full_url not in urls:
            urls.append(full_url)
    return urls


def _iter_lot_card_blocks(page_html: str) -> Iterable[str]:
    pattern = re.compile(
        r'<(li|div)[^>]*data-cy=["\']lot-card["\'][^>]*>(.*?)</\1>',
        re.IGNORECASE | re.DOTALL,
    )
    for match in pattern.finditer(page_html):
        yield match.group(0)
    if not pattern.search(page_html):
        for part in re.split(r'<li[^>]*>', page_html, flags=re.IGNORECASE):
            if "Lot" in part:
                end_idx = part.find("</li>")
                if end_idx != -1:
                    snippet = "<li>" + part[:end_idx] + "</li>"
                    yield snippet


def _wait_and_fetch(
    url: str,
    *,
    last_fetch: Optional[float],
    delay_seconds: float,
    http_client: TroostwatchHttpClient | None,
) -> Tuple[Optional[str], Optional[str], float]:
    if last_fetch is not None and delay_seconds > 0:
        elapsed = time.time() - last_fetch
        if elapsed < delay_seconds:
            time.sleep(delay_seconds - elapsed)
    html_text, error = _fetch_url(url, http_client=http_client)
    return html_text, error, time.time()


def _collect_pages(
    auction_url: str,
    *,
    max_pages: int | None,
    fetcher: HttpFetcher,
    verbose: bool,
    delay_seconds: float,
    http_client: TroostwatchHttpClient | None,
) -> Tuple[List[PageResult], List[str], List[str], Optional[float]]:
    pages: List[PageResult] = []
    errors: List[str] = []
    discovered_page_urls: List[str] = []
    last_fetch: Optional[float] = None

    def _fetch_html(url: str, *, apply_delay: bool) -> tuple[Optional[str], Optional[str]]:
        nonlocal last_fetch
        if http_client is not None:
            return _wait_and_fetch(
                url,
                last_fetch=last_fetch if apply_delay else None,
                delay_seconds=delay_seconds if apply_delay else 0,
                http_client=http_client,
            )[:2]

        result = fetcher.fetch_sync(url)
        if result.ok and result.text:
            return result.text, None
        return None, result.error or "empty response"

    first_html, first_err = _fetch_html(auction_url, apply_delay=False)
    last_fetch = time.time()
    if not first_html:
        errors.append(f"Failed to fetch first page {auction_url}: {first_err or 'empty response'}")
        return pages, errors, discovered_page_urls, last_fetch
    pages.append(PageResult(url=auction_url, html=first_html))

    discovered_page_urls = extract_page_urls(first_html, auction_url)
    page_urls = [url for url in discovered_page_urls if url != auction_url]
    target = max_pages if max_pages is not None else len(page_urls) + 1
    for url in page_urls:
        if len(pages) >= target:
            break
        html_text, err = _fetch_html(url, apply_delay=True)
        last_fetch = time.time()
        if html_text:
            pages.append(PageResult(url=url, html=html_text))
            _log(f"Fetched page {len(pages)} at {url}", verbose)
            continue

        # One retry when the first attempt fails
        html_text, err = _fetch_html(url, apply_delay=True)
        last_fetch = time.time()
        if html_text:
            pages.append(PageResult(url=url, html=html_text))
            _log(f"Fetched page {len(pages)} at {url}", verbose)
        else:
            errors.append(f"Failed to fetch page {url}: {err or 'empty response'}")
    return pages, errors, discovered_page_urls, last_fetch


def _extract_auction_title(page_html: str) -> Optional[str]:
    match_title = re.search(r"<title>(.*?)</title>", page_html, re.IGNORECASE | re.DOTALL)
    if match_title:
        return html.unescape(match_title.group(1)).strip()
    match_h1 = re.search(r"<h1[^>]*>(.*?)</h1>", page_html, re.IGNORECASE | re.DOTALL)
    if match_h1:
        return _strip_tags(match_h1.group(1)).strip()
    return None


def _upsert_auction(conn, auction_code: str, auction_url: str, auction_title: str | None) -> int:
    conn.execute(
        """
        INSERT INTO auctions (auction_code, title, url)
        VALUES (?, ?, ?)
        ON CONFLICT(auction_code) DO UPDATE SET
            title = excluded.title,
            url = excluded.url
        """,
        (auction_code, auction_title, auction_url),
    )
    cur = conn.execute("SELECT id FROM auctions WHERE auction_code = ?", (auction_code,))
    row = cur.fetchone()
    if not row:
        raise RuntimeError("Failed to retrieve auction id after upsert")
    return int(row[0])


def _choose_value(*values: Optional[str | float | int | bool]):
    for value in values:
        if value is not None:
            return value
    return None


def _hash_payload(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str, ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compute_listing_hash(card: LotCardData) -> str:
    payload = {
        "auction_code": card.auction_code,
        "lot_code": card.lot_code,
        "title": card.title,
        "state": card.state,
        "opens_at": card.opens_at,
        "closing_time_current": card.closing_time_current,
        "location_city": card.location_city,
        "location_country": card.location_country,
        "bid_count": card.bid_count,
        "price_eur": card.price_eur,
        "is_price_opening_bid": card.is_price_opening_bid,
    }
    return _hash_payload(payload)


def compute_detail_hash(detail: LotDetailData) -> str:
    payload = asdict(detail)
    return _hash_payload(payload)


def _upsert_lot(
    conn,
    auction_id: int,
    card: LotCardData,
    detail: LotDetailData,
    *,
    listing_hash: str,
    detail_hash: str,
    last_seen_at: str,
    detail_last_seen_at: str,
) -> None:
    lot_title = detail.title or card.title
    lot_url = detail.url or card.url
    lot_state = detail.state or card.state
    lot_opens_at = detail.opens_at or card.opens_at
    lot_closing_current = detail.closing_time_current or card.closing_time_current
    lot_closing_original = detail.closing_time_original
    lot_bid_count = detail.bid_count if detail.bid_count is not None else card.bid_count
    lot_opening_bid = _choose_value(detail.opening_bid_eur, card.price_eur if card.is_price_opening_bid else None)
    lot_current_bid = _choose_value(detail.current_bid_eur, card.price_eur)
    location_city = detail.location_city or card.location_city
    location_country = detail.location_country or card.location_country

    conn.execute(
        """
        INSERT INTO lots (
            auction_id, lot_code, title, url, state, status, opens_at,
            closing_time_current, closing_time_original, bid_count,
            opening_bid_eur, current_bid_eur, current_bidder_label,
            buyer_fee_percent, buyer_fee_vat_percent, vat_percent,
            awarding_state, total_example_price_eur, location_city,
            location_country, seller_allocation_note,
            listing_hash, detail_hash, last_seen_at, detail_last_seen_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(auction_id, lot_code) DO UPDATE SET
            title = excluded.title,
            url = excluded.url,
            state = excluded.state,
            status = excluded.status,
            opens_at = excluded.opens_at,
            closing_time_current = excluded.closing_time_current,
            closing_time_original = excluded.closing_time_original,
            bid_count = excluded.bid_count,
            opening_bid_eur = excluded.opening_bid_eur,
            current_bid_eur = excluded.current_bid_eur,
            current_bidder_label = excluded.current_bidder_label,
            buyer_fee_percent = excluded.buyer_fee_percent,
            buyer_fee_vat_percent = excluded.buyer_fee_vat_percent,
            vat_percent = excluded.vat_percent,
            awarding_state = excluded.awarding_state,
            total_example_price_eur = excluded.total_example_price_eur,
            location_city = excluded.location_city,
            location_country = excluded.location_country,
            seller_allocation_note = excluded.seller_allocation_note,
            listing_hash = excluded.listing_hash,
            detail_hash = excluded.detail_hash,
            last_seen_at = excluded.last_seen_at,
            detail_last_seen_at = excluded.detail_last_seen_at
        """,
        (
            auction_id,
            card.lot_code,
            lot_title,
            lot_url,
            lot_state,
            lot_state,
            lot_opens_at,
            lot_closing_current,
            lot_closing_original,
            lot_bid_count,
            lot_opening_bid,
            lot_current_bid,
            detail.current_bidder_label,
            detail.auction_fee_pct,
            detail.auction_fee_vat_pct,
            detail.vat_on_bid_pct,
            detail.state,
            detail.total_example_price_eur,
            location_city,
            location_country,
            detail.seller_allocation_note,
            listing_hash,
            detail_hash,
            last_seen_at,
            detail_last_seen_at,
        ),
    )


def sync_auction_to_db(
    db_path: str,
    auction_code: str,
    auction_url: str,
    max_pages: int | None = None,
    dry_run: bool | None = None,
    delay_seconds: float | None = None,
    max_concurrent_requests: int = 5,
    throttle_per_host: float | None = None,
    max_retries: int = 3,
    retry_backoff_base: float = 0.5,
    concurrency_mode: str = "asyncio",
    force_detail_refetch: bool = False,
    verbose: bool = False,
    http_client: TroostwatchHttpClient | None = None,
) -> SyncRunResult:
    pages_scanned = 0
    lots_scanned = 0
    lots_updated = 0
    errors: list[str] = []
    status = "failed"
    run_id: int | None = None
    discovered_page_urls: list[str] = []

    # fetcher will be created after reading config defaults so rate limits
    # (which may depend on `delay_seconds`) respect configuration values.

    with get_connection(db_path) as conn:
        ensure_core_schema(conn)
        ensure_schema(conn)

        def _notes_text() -> str | None:
            parts: list[str] = []
            if errors:
                parts.append("; ".join(errors))
            if discovered_page_urls:
                parts.append("pages: " + ", ".join(discovered_page_urls))
            return " | ".join(parts) if parts else None

        # If caller didn't explicitly provide runtime options, allow
        # configuration through `config.json` under the `sync` key.
        try:
            from ..db import get_config

            cfg = get_config()
            sync_cfg = cfg.get("sync", {}) if isinstance(cfg, dict) else {}
        except Exception:
            sync_cfg = {}

        if delay_seconds is None:
            delay_seconds = float(sync_cfg.get("delay_seconds", 0.5))
        if dry_run is None:
            dry_run = bool(sync_cfg.get("dry_run", False))
        if max_pages is None and "max_pages" in sync_cfg:
            raw_max = sync_cfg.get("max_pages")
            try:
                if raw_max is None:
                    max_pages = None
                else:
                    # Convert to str first to avoid passing None/unknown types to int()
                    parsed = int(str(raw_max))
                    # Treat non-positive values as "no limit"
                    max_pages = parsed if parsed > 0 else None
            except Exception:
                max_pages = None

        run_cur = conn.execute(
            """
            INSERT INTO sync_runs (
                auction_code, started_at, status, max_pages, dry_run
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (auction_code, iso_utcnow(), "running", max_pages, 1 if dry_run else 0),
        )
        lastrowid = run_cur.lastrowid
        if lastrowid is None:
            raise RuntimeError("Failed to insert sync_runs record; lastrowid is None")
        run_id = int(lastrowid)
        conn.commit()

        # Create fetcher here so it can honour any `delay_seconds` coming
        # from configuration.
        rate_limit = throttle_per_host
        if rate_limit is None and (delay_seconds is not None and delay_seconds > 0):
            rate_limit = 1.0 / delay_seconds
        fetcher = HttpFetcher(
            max_concurrent_requests=max_concurrent_requests,
            throttle_per_host=rate_limit,
            retry_attempts=max_retries,
            backoff_base_seconds=retry_backoff_base,
            concurrency_mode=concurrency_mode,
        )

        pages, page_errors, discovered_page_urls, last_fetch = _collect_pages(
            auction_url,
            max_pages=max_pages,
            fetcher=fetcher,
            verbose=verbose,
            delay_seconds=delay_seconds or 0,
            http_client=http_client,
        )
        errors.extend(page_errors)
        if not pages:
            finished_at = iso_utcnow()
            conn.execute(
                """
                    UPDATE sync_runs SET status = ?, finished_at = ?,
                        pages_scanned = ?, lots_scanned = ?, lots_updated = ?,
                        error_count = ?, notes = ?
                    WHERE id = ?
                    """,
                (
                    "failed",
                    finished_at,
                    pages_scanned,
                    lots_scanned,
                    lots_updated,
                    len(errors),
                    _notes_text(),
                    run_id,
                ),
            )
            conn.commit()
            return SyncRunResult(
                run_id=run_id,
                status="failed",
                pages_scanned=pages_scanned,
                lots_scanned=lots_scanned,
                lots_updated=lots_updated,
                error_count=len(errors),
                errors=errors,
            )

        pages_scanned = len(pages)
        auction_title = _extract_auction_title(pages[0].html)

        try:
            if not dry_run:
                conn.execute("BEGIN")
            auction_id = None
            existing_lots: Dict[str, Dict[str, Optional[str]]] = {}
            if not dry_run:
                auction_id = _upsert_auction(conn, auction_code, auction_url, auction_title)
                cur = conn.execute(
                    "SELECT lot_code, listing_hash, detail_hash FROM lots WHERE auction_id = ?",
                    (auction_id,),
                )
                for lot_code, listing_hash, detail_hash in cur.fetchall():
                    existing_lots[str(lot_code)] = {
                        "listing_hash": listing_hash,
                        "detail_hash": detail_hash,
                    }

            cards_needing_detail: list[tuple[LotCardData, str]] = []
            now_seen = iso_utcnow()
            url_parts = urlsplit(auction_url)
            base_url = f"{url_parts.scheme}://{url_parts.netloc}" if url_parts.scheme and url_parts.netloc else auction_url

            for page_idx, page in enumerate(pages, start=1):
                _log(
                    f"Processing page {page_idx}/{pages_scanned}: {page.url}",
                    verbose,
                )

                parsed_cards = list(parse_auction_page(page.html, base_url=base_url))
                if not parsed_cards:
                    parsed_cards = [
                        parse_lot_card(card_html, auction_code, base_url=base_url)
                        for card_html in _iter_lot_card_blocks(page.html)
                    ]

                for card in parsed_cards:
                    lots_scanned += 1
                    listing_hash = compute_listing_hash(card)
                    existing = existing_lots.get(card.lot_code)
                    needs_detail = force_detail_refetch or existing is None or existing.get("detail_hash") is None
                    if existing and existing.get("listing_hash") != listing_hash:
                        needs_detail = True

                    if not needs_detail and not dry_run and auction_id is not None:
                        conn.execute(
                            "UPDATE lots SET last_seen_at = ?, listing_hash = COALESCE(listing_hash, ?) WHERE auction_id = ? AND lot_code = ?",
                            (now_seen, listing_hash, auction_id, card.lot_code),
                        )
                        # No detail needed for this listing; update last seen and skip.
                        continue

                    if not card.url:
                        errors.append(
                            f"Failed to fetch detail for {card.lot_code} ({card.url}): missing detail URL"
                        )
                        continue

                    # Need to fetch detail HTML for this lot
                    detail_html, err, last_fetch = _wait_and_fetch(
                        card.url,
                        last_fetch=last_fetch,
                        delay_seconds=delay_seconds,
                        http_client=http_client,
                    )
                    if not detail_html:
                        errors.append(
                            f"Failed to fetch detail for {card.lot_code} ({card.url}): {err or 'empty response'}"
                        )
                        continue

                    cards_needing_detail.append((card, listing_hash))

            if cards_needing_detail:
                detail_results = asyncio.run(fetcher.fetch_many([card.url for card, _ in cards_needing_detail]))
            else:
                detail_results = []

            for (card, listing_hash), detail_result in zip(cards_needing_detail, detail_results):
                if not detail_result.ok or not detail_result.text:
                    errors.append(
                        f"Failed to fetch detail for {card.lot_code} ({card.url}): {detail_result.error or 'empty response'}"
                    )
                    continue
                detail = parse_lot_detail(detail_result.text, card.lot_code, base_url=auction_url)
                detail_hash = compute_detail_hash(detail)
                if not dry_run and auction_id is not None:
                    detail_seen_at = iso_utcnow()
                    _upsert_lot(
                        conn,
                        auction_id,
                        card,
                        detail,
                        listing_hash=listing_hash,
                        detail_hash=detail_hash,
                        last_seen_at=detail_seen_at,
                        detail_last_seen_at=detail_seen_at,
                    )
                    lots_updated += 1
                    _log(
                        f"  Upserted lot {card.lot_code}: bid €{detail.current_bid_eur or card.price_eur or 'n/a'}",
                        verbose,
                    )
            if not dry_run:
                conn.commit()
            status = "success"
        except Exception as exc:  # pragma: no cover - runtime protection
            errors.append(str(exc))
            if not dry_run:
                conn.rollback()
            status = "failed"
        finally:
            finished_at = iso_utcnow()
            conn.execute(
                """
                    UPDATE sync_runs SET status = ?, finished_at = ?,
                        pages_scanned = ?, lots_scanned = ?, lots_updated = ?,
                        error_count = ?, notes = ?
                    WHERE id = ?
                    """,
                (
                    status,
                    finished_at,
                    pages_scanned,
                    lots_scanned,
                    lots_updated,
                    len(errors),
                    _notes_text(),
                    run_id,
                ),
            )
            conn.commit()

        return SyncRunResult(
            run_id=run_id,
            status=status,
            pages_scanned=pages_scanned,
            lots_scanned=lots_scanned,
            lots_updated=lots_updated,
            error_count=len(errors),
            errors=errors,
        )


_STRIP_TAG_RE = re.compile(r"<[^>]+>")


def _strip_tags(text: str) -> str:
    return _STRIP_TAG_RE.sub("", text)

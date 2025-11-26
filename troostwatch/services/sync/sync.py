"""Synchronization module for fetching and persisting auction data."""

from __future__ import annotations

import asyncio
import hashlib
import html
import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from troostwatch.infrastructure.db import (
    ensure_core_schema,
    ensure_schema,
    get_connection,
    iso_utcnow,
)
from troostwatch.infrastructure.db.repositories import AuctionRepository, LotRepository
from troostwatch.infrastructure.http import TroostwatchHttpClient
from troostwatch.infrastructure.web.parsers import (
    LotCardData,
    LotDetailData,
    extract_page_urls,
    parse_auction_page,
    parse_lot_card,
    parse_lot_detail,
)

from .fetcher import HttpFetcher, RequestResult


@dataclass
class PageResult:
    url: str
    html: str


@dataclass
class SyncRunResult:
    run_id: Optional[int]
    status: str
    pages_scanned: int
    lots_scanned: int
    lots_updated: int
    error_count: int
    errors: List[str]


def _log(message: str, verbose: bool, log_path: Optional[str] = None) -> None:
    """Log a message to file and optionally to the console via logging.

    This function avoids direct print/click.echo calls to keep presentation
    logic out of the service layer. Instead, it uses the standard logging
    module which can be configured by the caller.
    """
    import logging

    timestamped = f"{iso_utcnow()} {message}"

    if log_path:
        try:
            log_file = Path(log_path)
            log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(log_file, "a", encoding="utf-8") as fp:
                fp.write(timestamped + "\n")
        except Exception:
            pass

    if not verbose:
        return

    logger = logging.getLogger("troostwatch.sync")
    logger.info(message)


def _fetch_url(
    url: str, http_client: Optional[TroostwatchHttpClient] = None
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
    except Exception as exc:
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
        for part in re.split(r"<li[^>]*>", page_html, flags=re.IGNORECASE):
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
    http_client: Optional[TroostwatchHttpClient],
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
    max_pages: Optional[int],
    fetcher: HttpFetcher,
    verbose: bool,
    delay_seconds: float,
    http_client: Optional[TroostwatchHttpClient],
    log_path: Optional[str] = None,
) -> Tuple[List[PageResult], List[str], List[str], Optional[float]]:
    pages: List[PageResult] = []
    errors: List[str] = []
    discovered_page_urls: List[str] = []
    last_fetch: Optional[float] = None

    def _fetch_html(
        url: str, *, apply_delay: bool
    ) -> Tuple[Optional[str], Optional[str]]:
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

    _log(f"Fetching page 1 at {auction_url}", verbose, log_path)
    first_html, first_err = _fetch_html(auction_url, apply_delay=False)
    last_fetch = time.time()
    if not first_html:
        errors.append(
            f"Failed to fetch first page {auction_url}: {first_err or 'empty response'}"
        )
        return pages, errors, discovered_page_urls, last_fetch
    pages.append(PageResult(url=auction_url, html=first_html))

    discovered_page_urls = extract_page_urls(first_html, auction_url)
    if discovered_page_urls:
        _log(
            f"Discovered {len(discovered_page_urls)} pagination page(s)",
            verbose,
            log_path,
        )
    page_urls = [url for url in discovered_page_urls if url != auction_url]
    target = max_pages if max_pages is not None else len(page_urls) + 1
    for url in page_urls:
        if len(pages) >= target:
            break
        _log(f"Fetching page {len(pages)+1} at {url}", verbose, log_path)
        html_text, err = _fetch_html(url, apply_delay=True)
        last_fetch = time.time()
        if html_text:
            pages.append(PageResult(url=url, html=html_text))
            _log(f"Fetched page {len(pages)} at {url}", verbose, log_path)
            continue

        html_text, err = _fetch_html(url, apply_delay=True)
        last_fetch = time.time()
        if html_text:
            pages.append(PageResult(url=url, html=html_text))
            _log(f"Fetched page {len(pages)} at {url}", verbose, log_path)
        else:
            errors.append(f"Failed to fetch page {url}: {err or 'empty response'}")
    return pages, errors, discovered_page_urls, last_fetch


def _extract_auction_title(page_html: str) -> Optional[str]:
    match_title = re.search(
        r"<title>(.*?)</title>", page_html, re.IGNORECASE | re.DOTALL
    )
    if match_title:
        return html.unescape(match_title.group(1)).strip()
    match_h1 = re.search(r"<h1[^>]*>(.*?)</h1>", page_html, re.IGNORECASE | re.DOTALL)
    if match_h1:
        return _strip_tags(match_h1.group(1)).strip()
    return None


_STRIP_TAG_RE = re.compile(r"<[^>]+>")


def _strip_tags(text: str) -> str:
    return _STRIP_TAG_RE.sub("", text)


def _upsert_auction(
    conn,
    auction_code: str,
    auction_url: str,
    auction_title: Optional[str],
    pagination_pages: Optional[List[str]] = None,
    *,
    repository: Optional[AuctionRepository] = None,
) -> int:
    repo = repository or AuctionRepository(conn)
    return repo.upsert(auction_code, auction_url, auction_title, pagination_pages)


def _choose_value(*values):
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


def _listing_detail_from_card(card: LotCardData) -> LotDetailData:
    """Build a minimal detail object from listing data when detail parsing fails."""
    opening_bid = card.price_eur if card.is_price_opening_bid else None
    current_bid = card.price_eur if opening_bid is None else None

    return LotDetailData(
        lot_code=card.lot_code,
        title=card.title,
        url=card.url,
        state=card.state,
        opens_at=card.opens_at,
        closing_time_current=card.closing_time_current,
        bid_count=card.bid_count,
        opening_bid_eur=opening_bid,
        current_bid_eur=current_bid,
        location_city=card.location_city,
        location_country=card.location_country,
    )


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
    repository: Optional[LotRepository] = None,
) -> None:
    repo = repository or LotRepository(conn)
    repo.upsert_from_parsed(
        auction_id,
        card,
        detail,
        listing_hash=listing_hash,
        detail_hash=detail_hash,
        last_seen_at=last_seen_at,
        detail_last_seen_at=detail_last_seen_at,
    )


def sync_auction_to_db(
    db_path: str,
    auction_code: str,
    auction_url: str,
    max_pages: Optional[int] = None,
    dry_run: Optional[bool] = None,
    delay_seconds: Optional[float] = None,
    max_concurrent_requests: int = 5,
    throttle_per_host: Optional[float] = None,
    max_retries: int = 3,
    retry_backoff_base: float = 0.5,
    concurrency_mode: str = "asyncio",
    force_detail_refetch: bool = False,
    verbose: Optional[bool] = None,
    log_path: Optional[str] = None,
    http_client: Optional[TroostwatchHttpClient] = None,
) -> SyncRunResult:
    pages_scanned = 0
    lots_scanned = 0
    lots_updated = 0
    errors: List[str] = []
    status = "success"
    run_id: Optional[int] = None
    discovered_page_urls: List[str] = []

    with get_connection(db_path) as conn:
        ensure_core_schema(conn)
        ensure_schema(conn)
        auction_repo = AuctionRepository(conn)
        lot_repo = LotRepository(conn)

        def _notes_text() -> Optional[str]:
            parts: List[str] = []
            if errors:
                parts.append("; ".join(errors))
            if discovered_page_urls:
                parts.append("pages: " + ", ".join(discovered_page_urls))
            return " | ".join(parts) if parts else None

        sync_cfg: Dict = {}
        if delay_seconds is None:
            delay_seconds = float(sync_cfg.get("delay_seconds", 0.5))
        if dry_run is None:
            dry_run = bool(sync_cfg.get("dry_run", False))
        if verbose is None:
            verbose = bool(sync_cfg.get("verbose", True))

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

        rate_limit = throttle_per_host
        if rate_limit is None and delay_seconds and delay_seconds > 0:
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
            log_path=log_path,
        )
        errors.extend(page_errors)
        pages_scanned = len(pages)
        if not pages:
            status = "failed"
            finished_at = iso_utcnow()
            conn.execute(
                """
                UPDATE sync_runs SET status = ?, finished_at = ?,
                    pages_scanned = ?, lots_scanned = ?, lots_updated = ?,
                    error_count = ?, notes = ?
                WHERE id = ?
                """,
                (status, finished_at, pages_scanned, lots_scanned, lots_updated,
                 len(errors), _notes_text(), run_id),
            )
            conn.commit()
            return SyncRunResult(
                run_id=run_id, status=status, pages_scanned=pages_scanned,
                lots_scanned=lots_scanned, lots_updated=lots_updated,
                error_count=len(errors), errors=errors,
            )

        auction_title = _extract_auction_title(pages[0].html)

        try:
            if not dry_run:
                conn.execute("BEGIN")
            auction_id: Optional[int] = None
            existing_lots: Dict[str, Dict[str, Optional[str]]] = {}
            if not dry_run:
                auction_id = _upsert_auction(
                    conn, auction_code, auction_url, auction_title,
                    pagination_pages=discovered_page_urls, repository=auction_repo,
                )
                cur = conn.execute(
                    "SELECT lot_code, listing_hash, detail_hash FROM lots WHERE auction_id = ?",
                    (auction_id,),
                )
                for lot_code, listing_hash, detail_hash in cur.fetchall():
                    existing_lots[str(lot_code)] = {
                        "listing_hash": listing_hash, "detail_hash": detail_hash,
                    }

            cards_needing_detail: List[Tuple[LotCardData, str, Optional[str]]] = []
            now_seen = iso_utcnow()
            url_parts = urlsplit(auction_url)
            base_url = (
                f"{url_parts.scheme}://{url_parts.netloc}"
                if url_parts.scheme and url_parts.netloc
                else auction_url
            )

            for page_idx, page in enumerate(pages, start=1):
                _log(f"Processing page {page_idx}/{pages_scanned}: {page.url}", verbose, log_path)
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
                    needs_detail = (
                        force_detail_refetch
                        or existing is None
                        or existing.get("detail_hash") is None
                    )
                    if existing and existing.get("listing_hash") != listing_hash:
                        needs_detail = True

                    if not needs_detail and not dry_run and auction_id is not None:
                        conn.execute(
                            "UPDATE lots SET last_seen_at = ?, listing_hash = COALESCE(listing_hash, ?) "
                            "WHERE auction_id = ? AND lot_code = ?",
                            (now_seen, listing_hash, auction_id, card.lot_code),
                        )
                        continue

                    if not card.url:
                        errors.append(f"Failed to fetch detail for {card.lot_code}: missing URL")
                        continue

                    detail_html, err, last_fetch = _wait_and_fetch(
                        card.url, last_fetch=last_fetch, delay_seconds=delay_seconds or 0,
                        http_client=http_client,
                    )
                    if not detail_html:
                        errors.append(f"Failed to fetch detail for {card.lot_code}: {err}")
                        if not dry_run and auction_id is not None:
                            detail = _listing_detail_from_card(card)
                            detail_hash = compute_detail_hash(detail)
                            last_seen = iso_utcnow()
                            _upsert_lot(
                                conn, auction_id, card, detail,
                                listing_hash=listing_hash, detail_hash=detail_hash,
                                last_seen_at=last_seen, detail_last_seen_at=last_seen,
                                repository=lot_repo,
                            )
                            lots_updated += 1
                        continue

                    cards_needing_detail.append((card, listing_hash, detail_html))

            for card, listing_hash, detail_text in cards_needing_detail:
                detail: LotDetailData
                detail_hash: Optional[str] = None
                try:
                    if detail_text:
                        detail = parse_lot_detail(detail_text, card.lot_code, base_url=auction_url)
                        detail_hash = compute_detail_hash(detail)
                    else:
                        detail = _listing_detail_from_card(card)
                except Exception as exc:
                    errors.append(f"Failed to parse detail for {card.lot_code}: {exc}")
                    detail = _listing_detail_from_card(card)

                if detail_hash is None:
                    detail_hash = compute_detail_hash(detail)

                if not dry_run and auction_id is not None:
                    detail_seen_at = iso_utcnow() if detail_text else None
                    last_seen = detail_seen_at or iso_utcnow()
                    _upsert_lot(
                        conn, auction_id, card, detail,
                        listing_hash=listing_hash, detail_hash=detail_hash,
                        last_seen_at=last_seen, detail_last_seen_at=detail_seen_at or last_seen,
                        repository=lot_repo,
                    )
                    lots_updated += 1
                    _log(f"  Upserted lot {card.lot_code}", verbose, log_path)

            if not dry_run:
                conn.commit()
        except Exception as exc:
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
                (status, finished_at, pages_scanned, lots_scanned, lots_updated,
                 len(errors), _notes_text(), run_id),
            )
            conn.commit()

        return SyncRunResult(
            run_id=run_id, status=status, pages_scanned=pages_scanned,
            lots_scanned=lots_scanned, lots_updated=lots_updated,
            error_count=len(errors), errors=errors,
        )


__all__ = [
    "HttpFetcher",
    "PageResult",
    "RequestResult",
    "SyncRunResult",
    "_listing_detail_from_card",
    "compute_detail_hash",
    "compute_listing_hash",
    "sync_auction_to_db",
]


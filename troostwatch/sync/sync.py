"""Synchronization module for fetching and persisting auction data."""

from __future__ import annotations

from dataclasses import dataclass
import html
import re
import time
from typing import Iterable, List, Optional, Tuple
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen

from ..db import ensure_core_schema, ensure_schema, get_connection, iso_utcnow
from ..parsers.lot_card import LotCardData, parse_lot_card
from ..parsers.lot_detail import LotDetailData, parse_lot_detail


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


def _fetch_url(url: str) -> Tuple[Optional[str], Optional[str]]:
    """Fetch the contents of a URL and return HTML plus any error message."""

    try:
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


def _wait_and_fetch(url: str, *, last_fetch: Optional[float], delay_seconds: float) -> Tuple[Optional[str], Optional[str], float]:
    if last_fetch is not None and delay_seconds > 0:
        elapsed = time.time() - last_fetch
        if elapsed < delay_seconds:
            time.sleep(delay_seconds - elapsed)
    html_text, error = _fetch_url(url)
    return html_text, error, time.time()


def _collect_pages(
    auction_url: str,
    *,
    max_pages: int | None,
    delay_seconds: float,
    verbose: bool,
) -> Tuple[List[PageResult], List[str], Optional[float]]:
    pages: List[PageResult] = []
    errors: List[str] = []
    last_fetch: Optional[float] = None

    first_html, err, last_fetch = _wait_and_fetch(
        auction_url, last_fetch=last_fetch, delay_seconds=0
    )
    if not first_html:
        errors.append(f"Failed to fetch first page {auction_url}: {err or 'empty response'}")
        return pages, errors, last_fetch
    pages.append(PageResult(url=auction_url, html=first_html))

    page_urls = _extract_page_urls(first_html, auction_url)
    target = max_pages if max_pages is not None else len(page_urls) + 1
    for url in page_urls:
        if len(pages) >= target:
            break
        for attempt in range(2):
            html_text, err, last_fetch = _wait_and_fetch(
                url, last_fetch=last_fetch, delay_seconds=delay_seconds
            )
            if html_text:
                pages.append(PageResult(url=url, html=html_text))
                _log(f"Fetched page {len(pages)} at {url}", verbose)
                break
            if attempt == 0:
                _log(f"Retrying page {url} after error: {err}", verbose)
        else:
            errors.append(f"Failed to fetch page {url}: {err or 'empty response'}")
    return pages, errors, last_fetch


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


def _upsert_lot(
    conn,
    auction_id: int,
    card: LotCardData,
    detail: LotDetailData,
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
            location_country, seller_allocation_note
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            seller_allocation_note = excluded.seller_allocation_note
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
        ),
    )


def sync_auction_to_db(
    db_path: str,
    auction_code: str,
    auction_url: str,
    max_pages: int | None = None,
    dry_run: bool = False,
    delay_seconds: float = 0.5,
    verbose: bool = False,
) -> SyncRunResult:
    pages_scanned = 0
    lots_scanned = 0
    lots_updated = 0
    errors: list[str] = []
    status = "failed"
    run_id: int | None = None

    with get_connection(db_path) as conn:
        ensure_core_schema(conn)
        ensure_schema(conn)

        run_cur = conn.execute(
            """
            INSERT INTO sync_runs (
                auction_code, started_at, status, max_pages, dry_run
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (auction_code, iso_utcnow(), "running", max_pages, 1 if dry_run else 0),
        )
        run_id = int(run_cur.lastrowid)
        conn.commit()

        pages, page_errors, last_fetch = _collect_pages(
            auction_url,
            max_pages=max_pages,
            delay_seconds=delay_seconds,
            verbose=verbose,
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
                    "; ".join(errors) if errors else None,
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
            if not dry_run:
                auction_id = _upsert_auction(conn, auction_code, auction_url, auction_title)

            for page_idx, page in enumerate(pages, start=1):
                _log(
                    f"Processing page {page_idx}/{pages_scanned}: {page.url}",
                    verbose,
                )
                for card_html in _iter_lot_card_blocks(page.html):
                    card = parse_lot_card(card_html, auction_code, base_url=auction_url)
                    lots_scanned += 1
                    detail_html, err, last_fetch = _wait_and_fetch(
                        card.url,
                        last_fetch=last_fetch,
                        delay_seconds=delay_seconds,
                    )
                    if not detail_html:
                        errors.append(
                            f"Failed to fetch detail for {card.lot_code} ({card.url}): {err or 'empty response'}"
                        )
                        continue
                    detail = parse_lot_detail(detail_html, card.lot_code, base_url=auction_url)
                    if not dry_run and auction_id is not None:
                        _upsert_lot(conn, auction_id, card, detail)
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
                "; ".join(errors) if errors else None,
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

"""Parser for Troostwatch lot cards."""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Iterable, Optional
from urllib.parse import urlsplit, urlencode, urlunsplit

from bs4 import BeautifulSoup

from troostwatch.infrastructure.observability.logging import get_logger
from . import utils

logger = get_logger(__name__)


def _extract_lot_number_from_url(url: str) -> str | None:
    """Extract the lot number from a Troostwijk lot URL.

    URL formats:
    - /l/description-AUCTION_CODE-LOT_NUMBER (e.g., /l/samsung-wm75a-A1-39500-1801)
    - /l/description-LOT_CODE (e.g., /l/daimler-benz-mb-trac-1300-voorlader-03T-SMD-1)

    Returns the lot identifier which may be numeric (1801) or alphanumeric (03T-SMD-1)
    """
    if not url:
        return None

    # Get the path part after /l/
    path = url.split("/l/")[-1] if "/l/" in url else url
    # Remove query string
    path = path.split("?")[0]

    # Try to extract the lot code from the end of the URL
    # Pattern: ends with alphanumeric lot code like 03T-SMD-1 or just 1801
    # Look for pattern after auction code (e.g., A1-39500-1801)
    match = re.search(r"-([A-Z]+\d*-\d+)-(\d+)$", path, re.IGNORECASE)
    if match:
        # URL has auction code followed by numeric lot number
        return match.group(2)

    # Try to match alphanumeric lot code pattern (e.g., 03T-SMD-1)
    match = re.search(r"-(\d+[A-Z]+-[A-Z]+-\d+)$", path, re.IGNORECASE)
    if match:
        return match.group(1)

    # Fallback: just get the last segment after the last hyphen
    match = re.search(r"-(\d+)$", path)
    if match:
        return match.group(1)

    return None


@dataclass
class LotCardData:
    """Data extracted from a lot card on an auction page."""

    auction_code: str
    lot_code: str
    title: str
    url: str
    state: str | None = None
    opens_at: str | None = None
    closing_time_current: str | None = None
    location_city: str | None = None
    location_country: str | None = None
    bid_count: int | None = None
    price_eur: float | None = None
    is_price_opening_bid: bool | None = None


def parse_lot_card(html: str, auction_code: str, base_url: str | None = None) -> LotCardData:
    """Parse a lot card from HTML matching Troostwijk's card markup."""

    soup = BeautifulSoup(html, "html.parser")
    card = soup.find(attrs={"data-cy": "lot-card"}) or soup
    card_html = str(card)
    utils.log_structure_signature(logger, "lot_card.card", card_html)

    try:
        def _text(selector: str) -> str:
            return utils.extract_by_data_cy(card, selector)

        display_id = _text("display-id-text")
        title_link = card.find(attrs={"data-cy": "title-link"})
        title = utils.extract_text(title_link)
        href = title_link.get("href", "") if title_link else ""
        url = str(href) if isinstance(href, str) else (href[0] if href else "")
        if base_url and url.startswith("/"):
            url = base_url.rstrip("/") + url

        # Extract lot number from URL, fallback to display_id
        lot_code = _extract_lot_number_from_url(url) or display_id

        state_attr = card.get("data-state") if hasattr(card, "get") else None
        state_text = (_text("state-chip") or (str(state_attr) if state_attr else "")).strip().lower()
        state: Optional[str]
        if state_text.startswith("run"):
            state = "running"
        elif state_text.startswith("sched") or state_text.startswith("open"):
            state = "scheduled"
        elif state_text.startswith("closed"):
            state = "closed"
        else:
            state = None

        bid_count = None
        bid_count_text = _text("bid-count-text")
        match_bid = re.search(r"(\d+)", bid_count_text)
        if match_bid:
            bid_count = int(match_bid.group(1))

        price_eur = None
        is_price_opening_bid = None
        bid_text = card.find(attrs={"data-cy": "bid-text"})
        if bid_text:
            amount_text = bid_text.get_text(" ", strip=True)
            match_price = re.search(r"€[^0-9]*([\d\.,]+)", amount_text)
            if match_price:
                price_eur = utils.parse_eur_to_float(match_price.group(0))
            label = " ".join(part.lower() for part in bid_text.stripped_strings if "€" not in part)
            if label:
                is_price_opening_bid = "open" in label

        opens_at = utils.parse_datetime_from_text(_text("opening-date-text"))
        closing_time_current = utils.parse_datetime_from_text(_text("closing-date-text"))

        city, country = utils.split_location(_text("location-text"))

        return LotCardData(
            auction_code=auction_code,
            lot_code=lot_code,
            title=title,
            url=url,
            state=state,
            opens_at=opens_at,
            closing_time_current=closing_time_current,
            location_city=city,
            location_country=country,
            bid_count=bid_count,
            price_eur=price_eur,
            is_price_opening_bid=is_price_opening_bid,
        )
    except Exception as exc:
        utils.record_parsing_error(logger, "lot_card.card", card_html, exc)
        raise


def parse_auction_page(html: str, base_url: str | None = None) -> Iterable[LotCardData]:
    """Parse all lot cards from a full auction page via ``__NEXT_DATA__``."""

    data = utils.extract_next_data(html)
    utils.log_structure_signature(logger, "auction.next_data", json.dumps(data, sort_keys=True))
    page_props = data.get("props", {}).get("pageProps", {})
    auction = page_props.get("auction", {})
    auction_code = auction.get("displayId")

    results = page_props.get("lots", {}).get("results") or []
    for lot in results:
        display_id = lot.get("displayId") or ""
        lot_auction_code = auction_code or "-".join(display_id.split("-")[:2])
        url_slug = lot.get("urlSlug") or ""
        url = url_slug
        if base_url and url_slug:
            url = f"{base_url.rstrip('/')}/l/{url_slug}"

        # Use displayId as the lot_code - this contains the full identifier
        # (e.g., "A1-39500-1801" or "03T-SMD-1")
        lot_code = display_id

        bids = lot.get("bidsCount")
        current_bid_amount = utils.amount_from_cents_dict(lot.get("currentBidAmount"))
        is_price_opening_bid = None
        if bids is not None:
            is_price_opening_bid = bids == 0

        status = (lot.get("biddingStatus") or "").lower()
        if status.startswith("bidding_open"):
            state = "running"
        elif status.startswith("published"):
            state = "scheduled"
        elif status.startswith("bidding_closed"):
            state = "closed"
        else:
            state = None

        location = lot.get("location") or {}
        loc_data = {**{"city": "", "countryCode": ""}, **location}
        city, country = utils.split_location(
            "{city}, {countryCode}".format(**loc_data)
        )
        country_code = (location.get("countryCode") or "").lower()
        country = utils.COUNTRY_CODES.get(country_code, country)

        yield LotCardData(
            auction_code=lot_auction_code,
            lot_code=lot_code,
            title=lot.get("title", ""),
            url=url,
            state=state,
            opens_at=utils.epoch_to_iso(lot.get("startDate")),
            closing_time_current=utils.epoch_to_iso(lot.get("endDate")),
            location_city=city,
            location_country=country,
            bid_count=bids,
            price_eur=current_bid_amount,
            is_price_opening_bid=is_price_opening_bid,
        )


def extract_page_urls(html: str, auction_url: str) -> list[str]:
    """Return all pagination URLs for an auction page."""

    page_urls: list[str] = []

    parsed_base = urlsplit(auction_url)
    auction_base = urlunsplit((parsed_base.scheme, parsed_base.netloc, parsed_base.path, "", ""))

    try:
        data = utils.extract_next_data(html)
    except Exception:
        data = None

    if isinstance(data, dict):
        page_props = data.get("props", {}).get("pageProps", {})
        lots_meta = page_props.get("lots", {}) if isinstance(page_props, dict) else {}
        pagination = (lots_meta.get("pagination") or page_props.get("pagination") or {})

        total_pages = (
            pagination.get("totalPages")
            or pagination.get("total_pages")
            or pagination.get("pages")
        )

        if total_pages is None:
            total_size = lots_meta.get("totalSize")
            page_size = lots_meta.get("pageSize")
            try:
                if total_size is not None and page_size:
                    total_pages = int((int(total_size) + int(page_size) - 1) // int(page_size))
            except Exception:
                total_pages = None

        try:
            total_pages_int = int(total_pages) if total_pages is not None else 1
        except Exception:
            total_pages_int = 1

        base_query: dict[str, str] = {}
        if parsed_base.query:
            from urllib.parse import parse_qsl
            base_query = {key: value for key, value in parse_qsl(parsed_base.query)}

        normalized_base = urlunsplit(
            (parsed_base.scheme, parsed_base.netloc, parsed_base.path, parsed_base.query, parsed_base.fragment)
        )
        page_urls.append(normalized_base)

        for page_num in range(2, total_pages_int + 1):
            query = base_query.copy()
            query["page"] = str(page_num)
            page_urls.append(
                urlunsplit(
                    (
                        parsed_base.scheme,
                        parsed_base.netloc,
                        parsed_base.path,
                        urlencode(query),
                        parsed_base.fragment,
                    )
                )
            )

    pattern = re.compile(r"href=[\"']([^\"']*?page=\d+)[\"']", re.IGNORECASE)
    for match in pattern.finditer(html):
        href = match.group(1)
        if href.startswith("http://") or href.startswith("https://"):
            full_url = href
        elif href.startswith("/"):
            full_url = auction_base.rstrip("/") + href
        else:
            if auction_base.endswith("/"):
                full_url = auction_base + href
            else:
                full_url = auction_base + ("/" if href and not href.startswith("?") else "") + href

        parsed_full = urlsplit(full_url)
        if parsed_full.path != parsed_base.path:
            continue
        if full_url not in page_urls:
            page_urls.append(full_url)

    return page_urls or [auction_url]


__all__ = ["LotCardData", "extract_page_urls", "parse_auction_page", "parse_lot_card"]

"""Placeholder parser for Troostwatch lot details.

Currently, this file contains stub definitions for the `LotDetailData` dataclass
and a `parse_lot_detail` function that should be implemented according to the
actual HTML structure of the Troostwijk site.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
import re
from datetime import datetime, timezone
from typing import Optional

from bs4 import BeautifulSoup

# Import helper functions from lot_card for parsing monetary and percent values
from .lot_card import (
    _parse_datetime_from_text,
    _parse_eur_to_float,
    _parse_nl_datetime,
    _parse_percent,
    _split_location,
)


@dataclass
class LotDetailData:
    """Data extracted from a lot detail page.

    Each attribute corresponds to a piece of information typically displayed
    on a Troostwijk lot detail page. If a value cannot be parsed from the
    provided HTML, the attribute will remain ``None``.
    """

    lot_code: str
    title: str
    url: str
    state: str | None = None
    opens_at: str | None = None
    closing_time_current: str | None = None
    closing_time_original: str | None = None
    bid_count: int | None = None
    opening_bid_eur: float | None = None
    current_bid_eur: float | None = None
    current_bidder_label: str | None = None
    vat_on_bid_pct: float | None = None
    auction_fee_pct: float | None = None
    auction_fee_vat_pct: float | None = None
    total_example_price_eur: float | None = None
    location_city: str | None = None
    location_country: str | None = None
    seller_allocation_note: str | None = None


def _strip_html_tags(text: str) -> str:
    """Remove HTML tags from a string.

    Args:
        text: The raw HTML string.

    Returns:
        The text with all HTML tags removed.
    """
    return re.sub(r"<[^>]+>", "", text)


_COUNTRY_CODES = {
    "de": "Germany",
    "nl": "Netherlands",
    "pl": "Poland",
}


def _epoch_to_iso(ts: int | float | None) -> Optional[str]:
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc).replace(tzinfo=None, second=0, microsecond=0).isoformat()
    except Exception:
        return None


def _parse_amount_field(value: dict | None) -> Optional[float]:
    if not value:
        return None
    if isinstance(value, dict):
        if "amount" in value and isinstance(value["amount"], (int, float)):
            return float(value["amount"]) / 100
        if "display" in value:
            parsed = _parse_eur_to_float(str(value["display"]))
            if parsed is not None:
                return parsed
    return None


def _extract_next_data(soup: BeautifulSoup) -> dict:
    script = soup.find("script", id="__NEXT_DATA__")
    if not script:
        return {}
    try:
        payload = script.string or script.get_text()
        return json.loads(payload)
    except json.JSONDecodeError:
        return {}


def parse_lot_detail(html: str, lot_code: str, base_url: str | None = None) -> LotDetailData:
    """Parse a lot detail page from Troostwijk HTML."""

    soup = BeautifulSoup(html, "html.parser")
    data = _extract_next_data(soup)
    page_props = data.get("props", {}).get("pageProps", {})
    lot = page_props.get("lot", {})
    fees = page_props.get("fees", {})

    title = lot.get("title") or _strip_html_tags(_parse_title_from_dom(soup))
    url = page_props.get("canonicalUrl") or _build_url(base_url, lot.get("urlSlug"), lot_code)

    status = (lot.get("status") or "").lower()
    if status.startswith("bidding_open"):
        state = "running"
    elif status.startswith("published"):
        state = "scheduled"
    elif status.startswith("bidding_closed"):
        state = "closed"
    else:
        state = None

    opens_at = _epoch_to_iso(lot.get("openingTime")) or _parse_datetime_from_text(_find_text_by_cy(soup, "opening-time"))
    closing_time_current = _epoch_to_iso(lot.get("closingTime")) or _parse_datetime_from_text(
        _find_text_by_cy(soup, "closing-time")
    )
    closing_time_original = _epoch_to_iso(lot.get("originalClosingTime"))

    bid_info = lot.get("bidInfo", {})
    bid_count = bid_info.get("bidCount")
    opening_bid_eur = _parse_amount_field(bid_info.get("openingBid"))
    current_bid_eur = _parse_amount_field(bid_info.get("currentBid"))
    current_bidder_label = bid_info.get("currentBidderLabel")

    vat_on_bid_pct = _parse_percent(str(fees.get("vatOnBidPct"))) if fees.get("vatOnBidPct") is not None else None
    auction_fee_pct = _parse_percent(str(fees.get("buyerFeePct"))) if fees.get("buyerFeePct") is not None else None
    auction_fee_vat_pct = _parse_percent(str(fees.get("buyerFeeVatPct"))) if fees.get("buyerFeeVatPct") is not None else None
    total_example_price_eur = _parse_amount_field(fees.get("totalExamplePrice"))

    location = lot.get("location", {})
    location_city = location.get("city") or None
    country_code = (location.get("countryCode") or "").lower()
    location_country = _COUNTRY_CODES.get(country_code)
    if not location_country:
        loc_text = _find_text_by_cy(soup, "item-location-text")
        city_text, country_text = _split_location(loc_text)
        location_city = location_city or city_text
        location_country = country_text

    seller_allocation_note = page_props.get("sellerAllocationNote") or _find_text_by_cy(soup, "item-collection-info-text")

    return LotDetailData(
        lot_code=lot.get("displayId") or lot_code,
        title=title or "",
        url=url or "",
        state=state,
        opens_at=opens_at,
        closing_time_current=closing_time_current,
        closing_time_original=closing_time_original,
        bid_count=bid_count,
        opening_bid_eur=opening_bid_eur,
        current_bid_eur=current_bid_eur,
        current_bidder_label=current_bidder_label,
        vat_on_bid_pct=vat_on_bid_pct,
        auction_fee_pct=auction_fee_pct,
        auction_fee_vat_pct=auction_fee_vat_pct,
        total_example_price_eur=total_example_price_eur,
        location_city=location_city,
        location_country=location_country,
        seller_allocation_note=seller_allocation_note,
    )


def _parse_title_from_dom(soup: BeautifulSoup) -> str:
    title_el = soup.find(["h1", "h2"], attrs={"data-cy": "item-title-text"}) or soup.find(["h1", "h2"])
    return title_el.get_text(" ", strip=True) if title_el else ""


def _build_url(base_url: str | None, slug: str | None, lot_code: str) -> Optional[str]:
    if slug and base_url:
        return f"{base_url.rstrip('/')}/l/{slug}"
    return None


def _find_text_by_cy(soup: BeautifulSoup, cy: str) -> str:
    el = soup.find(attrs={"data-cy": cy})
    return el.get_text(" ", strip=True) if el else ""
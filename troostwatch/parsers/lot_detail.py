"""Placeholder parser for Troostwatch lot details.

Currently, this file contains stub definitions for the `LotDetailData` dataclass
and a `parse_lot_detail` function that should be implemented according to the
actual HTML structure of the Troostwijk site.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from datetime import datetime
from typing import Optional

# Import helper functions from lot_card for parsing monetary and percent values
from .lot_card import _parse_eur_to_float, _parse_percent, _parse_nl_datetime


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


def parse_lot_detail(html: str, lot_code: str, base_url: str | None = None) -> LotDetailData:
    """Parse a lot detail page from HTML into a :class:`LotDetailData` instance.

    This parser attempts to extract information commonly found on a lot detail page,
    such as the title, current and opening bid amounts, bidder label, VAT and
    auction fee percentages, total example price, closing times and location.
    Since the Troostwijk layout may change over time, parsing is best‑effort and
    may need to be adjusted if fields are missing or misparsed.

    Args:
        html: The raw HTML of the lot detail page.
        lot_code: The lot code for this detail page.
        base_url: Optional base URL for constructing absolute links.

    Returns:
        A :class:`LotDetailData` instance populated with any parsed values.
    """
    # Initialize defaults
    title: str = ""
    url: str = ""
    state: Optional[str] = None
    opens_at: Optional[str] = None
    closing_time_current: Optional[str] = None
    closing_time_original: Optional[str] = None
    bid_count: Optional[int] = None
    opening_bid_eur: Optional[float] = None
    current_bid_eur: Optional[float] = None
    current_bidder_label: Optional[str] = None
    vat_on_bid_pct: Optional[float] = None
    auction_fee_pct: Optional[float] = None
    auction_fee_vat_pct: Optional[float] = None
    total_example_price_eur: Optional[float] = None
    location_city: Optional[str] = None
    location_country: Optional[str] = None
    seller_allocation_note: Optional[str] = None

    # Extract the title (often in an <h1> or <h2> tag)
    match_title = re.search(r"<h[12][^>]*>(.*?)</h[12]>", html, re.IGNORECASE | re.DOTALL)
    if match_title:
        title = _strip_html_tags(match_title.group(1)).strip()
    # Extract canonical URL from a rel link or use base_url and lot_code if available
    match_canonical = re.search(r'<link[^>]*rel=["\']canonical["\'][^>]*href=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if match_canonical:
        url = match_canonical.group(1)
    elif base_url and lot_code:
        url = f"{base_url.rstrip('/')}/lot/{lot_code}"
    # Determine lot state
    if re.search(r'closed|gesloten', html, re.IGNORECASE):
        state = 'closed'
    elif re.search(r'pending|wacht', html, re.IGNORECASE):
        state = 'pending'
    elif re.search(r'running|open', html, re.IGNORECASE):
        state = 'running'
    elif re.search(r'scheduled|gepland', html, re.IGNORECASE):
        state = 'scheduled'
    # Extract bid count (e.g., "5 bids" or "5 biedingen")
    match_bid_count = re.search(r'(?i)(\d+)\s*(bids?|biedingen?)', html)
    if match_bid_count:
        bid_count = int(match_bid_count.group(1))
    # Extract opening bid (e.g., "Opening bid € 100", "Startbod € 100")
    match_opening = re.search(r'(?i)(opening bid|startbod)\s*€\s*([0-9\.,]+)', html)
    if match_opening:
        opening_bid_eur = _parse_eur_to_float(match_opening.group(2))
    # Extract current bid (e.g., "Current bid € 200", "Huidig bod € 200")
    match_current = re.search(r'(?i)(current bid|huidig bod)\s*€\s*([0-9\.,]+)', html)
    if match_current:
        current_bid_eur = _parse_eur_to_float(match_current.group(2))
    # Extract current bidder label (e.g., "Highest bidder: John")
    match_bidder = re.search(r'(?i)(highest bidder|hoogste bieder)\s*:\s*([^<\n]+)', html)
    if match_bidder:
        current_bidder_label = _strip_html_tags(match_bidder.group(2)).strip()
    # Extract VAT on bid, auction fee and its VAT (percentages)
    match_vat = re.search(r'(?i)vat\s*:?\s*([0-9]+\.?[0-9]*%)', html)
    if match_vat:
        vat_on_bid_pct = _parse_percent(match_vat.group(1))
    match_fee = re.search(r'(?i)auction fee\s*:?\s*([0-9]+\.?[0-9]*%)', html)
    if match_fee:
        auction_fee_pct = _parse_percent(match_fee.group(1))
    match_fee_vat = re.search(r'(?i)auction fee vat\s*:?\s*([0-9]+\.?[0-9]*%)', html)
    if match_fee_vat:
        auction_fee_vat_pct = _parse_percent(match_fee_vat.group(1))
    # Extract total example price (e.g., "Total € 1.000,00")
    match_total = re.search(r'(?i)(total example price|totaalprijs)\s*€\s*([0-9\.,]+)', html)
    if match_total:
        total_example_price_eur = _parse_eur_to_float(match_total.group(2))
    # Extract opening and closing times (current and original) from common labels
    # Example: "Closes: 03 dec 2023 20:20" or "Closing time: 03 dec 2023 20:20"
    match_close = re.search(r'(?i)(closes|closing time|sluit)\s*:?\s*([0-9]{1,2}\s+\w+\s+\d{4}\s+\d{2}:\d{2})', html)
    if match_close:
        closing_time_current = _parse_nl_datetime(match_close.group(2))
    match_orig_close = re.search(r'(?i)(original closing time|oorspronkelijke sluiting)\s*:?\s*([0-9]{1,2}\s+\w+\s+\d{4}\s+\d{2}:\d{2})', html)
    if match_orig_close:
        closing_time_original = _parse_nl_datetime(match_orig_close.group(2))
    match_open = re.search(r'(?i)(opens|opening time|opent)\s*:?\s*([0-9]{1,2}\s+\w+\s+\d{4}\s+\d{2}:\d{2})', html)
    if match_open:
        opens_at = _parse_nl_datetime(match_open.group(2))
    # Extract location (city and country) from a string like "Location: Rotterdam, Netherlands"
    match_location = re.search(r'(?i)location\s*:?\s*([^<\n]+)', html)
    if match_location:
        loc = _strip_html_tags(match_location.group(1)).strip()
        # Split by comma if both city and country are present
        if "," in loc:
            city, country = [part.strip() for part in loc.split(",", 1)]
            location_city = city
            location_country = country
        else:
            location_city = loc
    # Extract seller allocation note if present
    match_note = re.search(r'(?i)(allocation|toewijzing)\s*:?\s*([^<\n]+)', html)
    if match_note:
        seller_allocation_note = _strip_html_tags(match_note.group(2)).strip()
    return LotDetailData(
        lot_code=lot_code,
        title=title,
        url=url,
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
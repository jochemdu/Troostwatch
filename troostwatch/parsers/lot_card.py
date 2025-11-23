"""Placeholder parser for Troostwatch lot cards.

Currently, this file contains stub definitions for the `LotCardData` dataclass
and a `parse_lot_card` function that should be implemented according to
the actual HTML structure of the Troostwijk site.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from datetime import datetime
from typing import Optional

# Mapping of Dutch month names to month numbers for date parsing
_MONTHS_NL = {
    "jan": 1,
    "feb": 2,
    "mrt": 3,
    "apr": 4,
    "mei": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "okt": 10,
    "nov": 11,
    "dec": 12,
}


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


# Helper functions for parsing common formats

def _parse_eur_to_float(text: str) -> Optional[float]:
    """Convert a string like "€ 1.234,56" to a float 1234.56.

    Returns None if the input cannot be parsed.
    """
    if not text:
        return None
    # Remove currency symbols and whitespace
    cleaned = text.replace("€", "").replace("Euro", "").strip()
    # Remove thousands separator and replace comma with dot
    cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_percent(text: str) -> Optional[float]:
    """Convert a percentage string like "21%" to a float 21.0.

    Returns None if the input cannot be parsed.
    """
    if not text:
        return None
    cleaned = text.strip().rstrip("%")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_nl_datetime(text: str) -> Optional[str]:
    """Parse a Dutch datetime string into ISO 8601 format.

    Example input: "03 dec 2023 20:20"
    Returns an ISO 8601 string like "2023-12-03T20:20:00" or None if
    parsing fails.
    """
    if not text:
        return None
    parts = text.strip().split()
    if len(parts) < 4:
        return None
    try:
        day = int(parts[0])
        month = _MONTHS_NL[parts[1].lower()[:3]]
        year = int(parts[2])
        time_part = parts[3]
        dt_str = f"{year:04d}-{month:02d}-{day:02d}T{time_part}:00"
        # Validate by parsing with datetime
        datetime.fromisoformat(dt_str)
        return dt_str
    except Exception:
        return None


def parse_lot_card(html: str, auction_code: str, base_url: str | None = None) -> LotCardData:
    """Parse a lot card from HTML.

    This stub returns a `LotCardData` instance with minimal fields filled.
    The actual parser should extract the necessary information from the HTML.

    Args:
        html: The HTML of the lot card.
        auction_code: The auction code for which this lot belongs.
        base_url: Optional base URL for constructing absolute links.

    Returns:
        A LotCardData instance.
    """
    # Attempt to extract lot code and title via simple patterns. These
    # patterns may need refinement based on real HTML; they are intended
    # as a starting point.
    lot_code: str = ""
    title: str = ""
    url: str = ""
    # Extract the first anchor tag's href as the URL
    match_href = re.search(r'<a[^>]*href=["\'](?P<url>[^"\']+)["\']', html, re.IGNORECASE)
    if match_href:
        url = match_href.group("url")
        # Prepend base_url if needed
        if base_url and url.startswith("/"):
            url = base_url.rstrip("/") + url
    # Extract lot code (e.g., "Lot 1234")
    match_lot = re.search(r'Lot\s*([\w-]+)', html, re.IGNORECASE)
    if match_lot:
        lot_code = match_lot.group(1)
    # Extract title from a heading or strong tag
    match_title = re.search(r'<h[1-6][^>]*>(.*?)</h[1-6]>', html, re.IGNORECASE | re.DOTALL)
    if match_title:
        # Remove HTML tags from title
        title_raw = re.sub(r'<[^>]+>', '', match_title.group(1))
        title = title_raw.strip()
    # Extract current price (Euro) if present
    match_price = re.search(r'€\s?[0-9\.,]+', html)
    price_eur = _parse_eur_to_float(match_price.group()) if match_price else None
    # Extract bid count
    match_bid_count = re.search(r'(?i)(\d+)\s*bids?', html)
    bid_count = int(match_bid_count.group(1)) if match_bid_count else None
    # Attempt to determine state based on keywords
    state: Optional[str] = None
    if re.search(r'closed|gesloten', html, re.IGNORECASE):
        state = 'closed'
    elif re.search(r'running|open', html, re.IGNORECASE):
        state = 'running'
    elif re.search(r'scheduled|gepland', html, re.IGNORECASE):
        state = 'scheduled'
    # Return populated dataclass
    return LotCardData(
        auction_code=auction_code,
        lot_code=lot_code,
        title=title,
        url=url,
        state=state,
        bid_count=bid_count,
        price_eur=price_eur,
    )
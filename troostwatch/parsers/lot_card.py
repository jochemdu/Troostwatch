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

from bs4 import BeautifulSoup

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


def _parse_datetime_from_text(text: str) -> Optional[str]:
    """Extract and parse a Dutch datetime from freeform text."""

    if not text:
        return None
    match = re.search(r"(\d{1,2}\s+\w+\s+\d{4}\s+\d{2}:\d{2})", text)
    if not match:
        return None
    return _parse_nl_datetime(match.group(1))


def _split_location(text: str) -> tuple[Optional[str], Optional[str]]:
    """Split a location string into city and country components."""

    if not text:
        return None, None
    if "," in text:
        city, country = [part.strip() for part in text.split(",", 1)]
        return city or None, country or None
    return text.strip() or None, None


def parse_lot_card(html: str, auction_code: str, base_url: str | None = None) -> LotCardData:
    """Parse a lot card from HTML matching Troostwijk's card markup."""

    soup = BeautifulSoup(html, "html.parser")
    card = soup.find(attrs={"data-cy": "lot-card"}) or soup

    def _text(selector: str) -> str:
        el = card.find(attrs={"data-cy": selector})
        return el.get_text(" ", strip=True) if el else ""

    lot_code = _text("display-id-text")
    title_link = card.find(attrs={"data-cy": "title-link"})
    title = title_link.get_text(" ", strip=True) if title_link else ""
    url = title_link.get("href", "") if title_link else ""
    if base_url and url.startswith("/"):
        url = base_url.rstrip("/") + url

    state_text = (_text("state-chip") or card.get("data-state", "")).strip().lower()
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
            price_eur = _parse_eur_to_float(match_price.group(0))
        label = " ".join(part.lower() for part in bid_text.stripped_strings if "€" not in part)
        if label:
            is_price_opening_bid = "open" in label

    opens_at = _parse_datetime_from_text(_text("opening-date-text"))
    closing_time_current = _parse_datetime_from_text(_text("closing-date-text"))

    city, country = _split_location(_text("location-text"))

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
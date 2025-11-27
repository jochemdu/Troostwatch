"""Reusable parsing helpers for Troostwatch parsers.

This module centralizes common parsing tasks like currency/percent parsing,
Dutch datetime parsing with timezone handling, HTML text extraction helpers,
and lightweight structure checksums to detect markup drift at runtime.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from typing import Iterable

from bs4 import BeautifulSoup, Tag

from troostwatch.infrastructure.observability.logging import get_logger

LOGGER = get_logger(__name__)

MONTHS_NL = {
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

COUNTRY_CODES = {
    "de": "Germany",
    "nl": "Netherlands",
    "pl": "Poland",
}


# HTML helpers


def extract_text(element, default: str = "", separator: str = " ") -> str:
    """Return flattened text from a BeautifulSoup element.

    Args:
        element: A BeautifulSoup Tag or NavigableString.
        default: Value returned when the element is falsy.
        separator: Separator passed to ``get_text``.
    """

    if not element:
        return default
    return element.get_text(separator, strip=True)


def extract_by_data_cy(
    soup: BeautifulSoup | Tag, data_cy: str, default: str = ""
) -> str:
    """Find an element by ``data-cy`` attribute and return its text."""

    element = soup.find(attrs={"data-cy": data_cy})
    return extract_text(element, default=default)


# Numeric and currency helpers


def parse_eur_to_float(text: str) -> float | None:
    """Convert a string like "€ 1.234,56" to a float 1234.56."""

    if not text:
        return None
    cleaned = text.replace("€", "").replace("Euro", "").strip()
    cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def amount_from_cents_dict(amount: dict | None) -> float | None:
    """Convert a Troostwijk ``{"cents": 19000}`` amount dictionary to float euros."""

    if not isinstance(amount, dict):
        return None
    cents = amount.get("cents")
    if isinstance(cents, (int, float)):
        return float(cents) / 100
    return None


def parse_percent(text: str) -> float | None:
    """Convert a percentage string like "21%" to a float 21.0."""

    if not text:
        return None
    cleaned = text.strip().rstrip("%")
    try:
        return float(cleaned)
    except ValueError:
        return None


# Datetime helpers


def _format_iso(dt: datetime, strip_timezone: bool) -> str:
    if strip_timezone:
        dt = dt.replace(tzinfo=None)
    return dt.replace(second=0, microsecond=0).isoformat()


def epoch_to_iso(
    ts: int | float | None, tz: timezone = timezone.utc, strip_timezone: bool = True
) -> str | None:
    """Convert epoch seconds or milliseconds to an ISO-8601 string with optional timezone stripping.

    Automatically detects if timestamp is in milliseconds (>1e12) and converts accordingly.
    """

    if ts is None:
        return None
    try:
        # Detect milliseconds (timestamps > year 33658 in seconds, ~1e12)
        if ts > 1_000_000_000_000:
            ts = ts / 1000
        dt = datetime.fromtimestamp(ts, tz=tz)
        return _format_iso(dt, strip_timezone)
    except Exception:
        return None


def parse_nl_datetime(
    text: str, tz: timezone = timezone.utc, strip_timezone: bool = True
) -> str | None:
    """Parse a Dutch datetime string into ISO 8601 format with timezone support."""

    if not text:
        return None
    parts = text.strip().split()
    if len(parts) < 4:
        return None
    try:
        day = int(parts[0])
        month = MONTHS_NL[parts[1].lower()[:3]]
        year = int(parts[2])
        hour, minute = [int(part) for part in parts[3].split(":", 1)]
        dt = datetime(year, month, day, hour, minute, tzinfo=tz)
        return _format_iso(dt, strip_timezone)
    except Exception:
        return None


def parse_datetime_from_text(
    text: str, tz: timezone = timezone.utc, strip_timezone: bool = True
) -> str | None:
    """Extract and parse a Dutch datetime from freeform text."""

    if not text:
        return None
    match = re.search(r"(\d{1,2}\s+\w+\s+\d{4}\s+\d{2}:\d{2})", text)
    if not match:
        return None
    return parse_nl_datetime(match.group(1), tz=tz, strip_timezone=strip_timezone)


def split_location(text: str) -> tuple[str | None, str | None]:
    """Split a location string into city and country components."""

    if not text:
        return None, None
    if "," in text:
        city, country = [part.strip() for part in text.split(",", 1)]
        return city or None, country or None
    return text.strip() or None, None


# JSON helpers


def extract_next_data(html: str | BeautifulSoup) -> dict:
    """Load ``__NEXT_DATA__`` JSON from a page when present."""

    soup = BeautifulSoup(html, "html.parser") if isinstance(html, str) else html
    script = soup.find("script", id="__NEXT_DATA__")
    if not script:
        return {}
    try:
        payload = script.string or script.get_text()
        return json.loads(payload)
    except Exception:
        return {}


# Diagnostics helpers


def structure_checksum(html_fragment: str) -> str:
    """Return a stable checksum for a markup fragment."""

    normalized = re.sub(r"\s+", " ", html_fragment or "").strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def log_structure_signature(
    logger: logging.Logger, section: str, html_fragment: str
) -> None:
    """Log a checksum for a specific parser section to detect layout drift."""

    checksum = structure_checksum(html_fragment)
    logger.info("structure-signature", extra={"section": section, "checksum": checksum})


def record_parsing_error(
    logger: logging.Logger, section: str, html_fragment: str, error: Exception
) -> None:
    """Log a parsing failure with a checksum and a clipped HTML snippet."""

    checksum = structure_checksum(html_fragment)
    snippet = (html_fragment or "").strip()
    if len(snippet) > 500:
        snippet = snippet[:500] + "…"
    logger.error(
        "parsing-error",
        extra={
            "section": section,
            "checksum": checksum,
            "snippet": snippet,
            "error": str(error),
        },
    )


def first_item(iterable: Iterable, default=None):
    """Return the first item from an iterable or a default value."""

    for item in iterable:
        return item
    return default

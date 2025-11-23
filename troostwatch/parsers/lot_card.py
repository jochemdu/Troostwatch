"""Placeholder parser for Troostwatch lot cards.

Currently, this file contains stub definitions for the `LotCardData` dataclass
and a `parse_lot_card` function that should be implemented according to
the actual HTML structure of the Troostwijk site.
"""

from __future__ import annotations

from dataclasses import dataclass


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
    # TODO: implement real parsing logic
    return LotCardData(
        auction_code=auction_code,
        lot_code="",
        title="",
        url="",
    )
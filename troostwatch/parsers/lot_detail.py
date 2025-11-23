"""Placeholder parser for Troostwatch lot details.

Currently, this file contains stub definitions for the `LotDetailData` dataclass
and a `parse_lot_detail` function that should be implemented according to the
actual HTML structure of the Troostwijk site.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LotDetailData:
    """Data extracted from a lot detail page."""

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


def parse_lot_detail(html: str, lot_code: str, base_url: str | None = None) -> LotDetailData:
    """Parse a lot detail page from HTML.

    This stub returns a `LotDetailData` instance with minimal fields filled.
    The actual parser should extract the necessary information from the HTML.

    Args:
        html: The HTML of the lot detail page.
        lot_code: The lot code.
        base_url: Optional base URL for constructing absolute links.

    Returns:
        A LotDetailData instance.
    """
    # TODO: implement real parsing logic
    return LotDetailData(
        lot_code=lot_code,
        title="",
        url="",
    )
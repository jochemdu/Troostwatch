"""Facade for lot card parsing.

Re-exports :mod:`troostwatch.parsers.lot_card` under the infrastructure namespace
so downstream imports can migrate gradually.
"""

from troostwatch.parsers.lot_card import (
    LotCardData,
    extract_page_urls,
    parse_auction_page,
    parse_lot_card,
)

__all__ = ["LotCardData", "extract_page_urls", "parse_auction_page", "parse_lot_card"]

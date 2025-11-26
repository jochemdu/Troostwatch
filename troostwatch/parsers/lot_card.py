"""Legacy lot card parser - deprecated.

This module re-exports from ``troostwatch.infrastructure.web.parsers.lot_card``.
"""

from troostwatch.infrastructure.web.parsers.lot_card import (
    LotCardData,
    extract_page_urls,
    logger,
    parse_auction_page,
    parse_lot_card,
)

__all__ = ["LotCardData", "extract_page_urls", "parse_auction_page", "parse_lot_card"]

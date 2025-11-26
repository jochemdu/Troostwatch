"""Legacy lot detail parser - deprecated.

This module re-exports from ``troostwatch.infrastructure.web.parsers.lot_detail``.
"""

from troostwatch.infrastructure.web.parsers.lot_detail import (
    LotDetailData,
    logger,
    parse_lot_detail,
)

__all__ = ["LotDetailData", "parse_lot_detail"]

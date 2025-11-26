"""Legacy parsers namespace.

This package is deprecated. Import from ``troostwatch.infrastructure.web.parsers``
instead. This module re-exports the new implementations for backward compatibility.
"""

import warnings

warnings.warn(
    "`troostwatch.parsers` is deprecated; import from "
    "`troostwatch.infrastructure.web.parsers` instead.",
    DeprecationWarning,
    stacklevel=2,
)

from troostwatch.infrastructure.web.parsers import (
    COUNTRY_CODES,
    MONTHS_NL,
    LotCardData,
    LotDetailData,
    amount_from_cents_dict,
    epoch_to_iso,
    extract_by_data_cy,
    extract_next_data,
    extract_page_urls,
    extract_text,
    first_item,
    log_structure_signature,
    parse_auction_page,
    parse_datetime_from_text,
    parse_eur_to_float,
    parse_lot_card,
    parse_lot_detail,
    parse_nl_datetime,
    parse_percent,
    record_parsing_error,
    split_location,
    structure_checksum,
)

__all__ = [
    "COUNTRY_CODES",
    "MONTHS_NL",
    "LotCardData",
    "LotDetailData",
    "amount_from_cents_dict",
    "epoch_to_iso",
    "extract_by_data_cy",
    "extract_next_data",
    "extract_page_urls",
    "extract_text",
    "first_item",
    "log_structure_signature",
    "parse_auction_page",
    "parse_datetime_from_text",
    "parse_eur_to_float",
    "parse_lot_card",
    "parse_lot_detail",
    "parse_nl_datetime",
    "parse_percent",
    "record_parsing_error",
    "split_location",
    "structure_checksum",
]
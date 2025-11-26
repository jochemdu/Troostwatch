"""Legacy parser utilities - deprecated.

This module re-exports from ``troostwatch.infrastructure.web.parsers.utils``.
"""

from troostwatch.infrastructure.web.parsers.utils import (
    COUNTRY_CODES,
    LOGGER,
    MONTHS_NL,
    amount_from_cents_dict,
    epoch_to_iso,
    extract_by_data_cy,
    extract_next_data,
    extract_text,
    first_item,
    log_structure_signature,
    parse_datetime_from_text,
    parse_eur_to_float,
    parse_nl_datetime,
    parse_percent,
    record_parsing_error,
    split_location,
    structure_checksum,
)

__all__ = [
    "COUNTRY_CODES",
    "LOGGER",
    "MONTHS_NL",
    "amount_from_cents_dict",
    "epoch_to_iso",
    "extract_by_data_cy",
    "extract_next_data",
    "extract_text",
    "first_item",
    "log_structure_signature",
    "parse_datetime_from_text",
    "parse_eur_to_float",
    "parse_nl_datetime",
    "parse_percent",
    "record_parsing_error",
    "split_location",
    "structure_checksum",
]

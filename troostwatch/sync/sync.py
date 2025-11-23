"""Placeholder synchronization module.

This module currently contains stub functions for fetching auction pages,
parsing the content and persisting it to the database. The actual
implementation should download HTML, call the parsers and insert data
into the SQLite database.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable


def sync_auction_to_db(
    db_path: str,
    auction_code: str,
    auction_url: str,
    max_pages: int | None = None,
    dry_run: bool = False,
    delay_seconds: float = 0.5,
) -> None:
    """Synchronize a Troostwijk auction into a SQLite database.

    This stub function does nothing except raise a NotImplementedError.

    Args:
        db_path: Path to the SQLite database.
        auction_code: The auction code to sync.
        auction_url: The URL of the auction page.
        max_pages: Optional limit on the number of pages to fetch.
        dry_run: If True, do not write to the database.
        delay_seconds: Delay between HTTP requests in seconds.

    Raises:
        NotImplementedError: Always, since this is a stub.
    """
    raise NotImplementedError("sync_auction_to_db is not yet implemented.")
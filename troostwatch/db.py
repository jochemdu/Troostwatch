"""Database utilities for Troostwatch.

This module provides placeholder functionality for connecting to a SQLite database.
The actual project should implement helper functions to open connections,
configure SQLite settings (foreign keys, journal mode) and perform migrations.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator


@contextmanager
def get_connection(db_path: str) -> Iterator[sqlite3.Connection]:
    """Context manager yielding a SQLite connection.

    Args:
        db_path: Path to the SQLite database file.

    Yields:
        A sqlite3.Connection instance.
    """
    conn = sqlite3.connect(db_path)
    try:
        yield conn
    finally:
        conn.close()
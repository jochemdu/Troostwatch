"""Database utilities for Troostwatch.

This module provides placeholder functionality for connecting to a SQLite database.
The actual project should implement helper functions to open connections,
configure SQLite settings (foreign keys, journal mode) and perform migrations.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Iterable, Optional, List, Dict

SCHEMA_BUYERS_SQL = """
CREATE TABLE IF NOT EXISTS buyers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT NOT NULL UNIQUE,
    name TEXT,
    notes TEXT
);
"""


@contextmanager
def get_connection(db_path: str) -> Iterator[sqlite3.Connection]:
    """Context manager yielding a configured SQLite connection.

    This helper ensures that foreign keys are enforced and that a
    write-ahead log is used to improve concurrency.

    Args:
        db_path: Path to the SQLite database file.

    Yields:
        A configured sqlite3.Connection instance.
    """
    # Ensure parent directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        # Enable WAL and foreign keys
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        yield conn
    finally:
        conn.close()


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Create required tables if they do not already exist.

    Currently ensures the buyers table exists. Call this before using any
    helper functions that manipulate the database.

    Args:
        conn: Open sqlite3.Connection.
    """
    conn.executescript(SCHEMA_BUYERS_SQL)


def add_buyer(conn: sqlite3.Connection, label: str, name: Optional[str] = None, notes: Optional[str] = None) -> None:
    """Add a buyer to the database.

    If a buyer with the same label already exists, this function does nothing.

    Args:
        conn: Open sqlite3.Connection.
        label: Unique label for the buyer.
        name: Optional full name of the buyer.
        notes: Optional free‑form notes.
    """
    ensure_schema(conn)
    conn.execute(
        "INSERT OR IGNORE INTO buyers (label, name, notes) VALUES (?, ?, ?)",
        (label, name, notes),
    )
    conn.commit()


def list_buyers(conn: sqlite3.Connection) -> List[Dict[str, Optional[str]]]:
    """Return a list of all buyers in the database.

    Args:
        conn: Open sqlite3.Connection.

    Returns:
        A list of dictionaries with keys: id, label, name, notes.
    """
    ensure_schema(conn)
    cur = conn.execute("SELECT id, label, name, notes FROM buyers ORDER BY id")
    columns = [c[0] for c in cur.description]
    return [dict(zip(columns, row)) for row in cur.fetchall()]


def delete_buyer(conn: sqlite3.Connection, label: str) -> None:
    """Delete a buyer from the database by label.

    Args:
        conn: Open sqlite3.Connection.
        label: The label of the buyer to remove.
    """
    ensure_schema(conn)
    conn.execute("DELETE FROM buyers WHERE label = ?", (label,))
    conn.commit()
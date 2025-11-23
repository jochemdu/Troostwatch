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

SCHEMA_POSITIONS_SQL = """
CREATE TABLE IF NOT EXISTS my_lot_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    buyer_id INTEGER NOT NULL,
    lot_id INTEGER NOT NULL,
    track_active INTEGER NOT NULL DEFAULT 1,
    max_budget_total_eur REAL,
    my_highest_bid_eur REAL,
    FOREIGN KEY (buyer_id) REFERENCES buyers (id) ON DELETE CASCADE,
    FOREIGN KEY (lot_id) REFERENCES lots (id) ON DELETE CASCADE,
    UNIQUE (buyer_id, lot_id)
);
"""
# Relative path to the core schema used by sync operations. This includes
# definitions for auctions and lots tables. We compute the path relative to
# this file so it works regardless of the working directory from which
# functions are invoked.
from pathlib import Path as _Path
_SCHEMA_FILE = (_Path(__file__).resolve().parents[2] / "schema" / "schema.sql").as_posix()


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
    conn.executescript(SCHEMA_POSITIONS_SQL)


def ensure_core_schema(conn: sqlite3.Connection) -> None:
    """Ensure the core auction and lot tables exist in the database.

    This helper reads the SQL schema from the schema.sql file in the
    repository root and executes it. It is idempotent: missing tables will
    be created, existing tables remain untouched.

    Args:
        conn: An open sqlite3.Connection.
    """
    # Read the schema file only if it exists. The repository should always
    # ship this file, but we guard against missing files to avoid crashing.
    try:
        with open(_SCHEMA_FILE, "r", encoding="utf-8") as f:
            script = f.read()
        conn.executescript(script)
    except FileNotFoundError:
        # If the schema file is not present (e.g., packaged differently), we
        # silently do nothing. Sync operations will create necessary tables if
        # possible.
        pass


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

# Position management helpers

def _get_buyer_id(conn: sqlite3.Connection, label: str) -> Optional[int]:
    """Return the row ID of a buyer given its label, or None if not found."""
    ensure_schema(conn)
    cur = conn.execute("SELECT id FROM buyers WHERE label = ?", (label,))
    row = cur.fetchone()
    return row[0] if row else None

def _get_lot_id(conn: sqlite3.Connection, lot_code: str, auction_code: Optional[str] = None) -> Optional[int]:
    """Return the row ID of a lot given its lot code and optional auction code.

    If multiple lots share the same lot code across auctions and an auction code
    is not provided, the first matching lot ID is returned. None is returned if
    no matching lot is found.
    """
    ensure_core_schema(conn)
    query = "SELECT l.id FROM lots l JOIN auctions a ON l.auction_id = a.id WHERE l.lot_code = ?"
    params: List = [lot_code]
    if auction_code is not None:
        query += " AND a.auction_code = ?"
        params.append(auction_code)
    cur = conn.execute(query, tuple(params))
    row = cur.fetchone()
    return row[0] if row else None

def add_position(
    conn: sqlite3.Connection,
    buyer_label: str,
    lot_code: str,
    auction_code: Optional[str] = None,
    track_active: bool = True,
    max_budget_total_eur: Optional[float] = None,
    my_highest_bid_eur: Optional[float] = None,
) -> None:
    """Insert or update a lot position for the given buyer and lot.

    Args:
        conn: An open SQLite connection.
        buyer_label: Label of the buyer who owns the position.
        lot_code: The code of the lot to track.
        auction_code: Optional auction code to disambiguate lots.
        track_active: Whether this lot should be included in exposure calculations.
        max_budget_total_eur: Optional maximum total budget for the lot.
        my_highest_bid_eur: Optional highest bid placed by the buyer on this lot.
    """
    ensure_schema(conn)
    buyer_id = _get_buyer_id(conn, buyer_label)
    if buyer_id is None:
        raise ValueError(f"Buyer with label '{buyer_label}' does not exist")
    lot_id = _get_lot_id(conn, lot_code, auction_code)
    if lot_id is None:
        raise ValueError(f"Lot with code '{lot_code}' not found (auction: {auction_code})")
    # Upsert logic: insert or replace existing record
    conn.execute(
        """
        INSERT INTO my_lot_positions (buyer_id, lot_id, track_active, max_budget_total_eur, my_highest_bid_eur)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(buyer_id, lot_id) DO UPDATE SET
            track_active = excluded.track_active,
            max_budget_total_eur = excluded.max_budget_total_eur,
            my_highest_bid_eur = excluded.my_highest_bid_eur
        """,
        (buyer_id, lot_id, 1 if track_active else 0, max_budget_total_eur, my_highest_bid_eur),
    )
    conn.commit()

def list_positions(conn: sqlite3.Connection, buyer_label: Optional[str] = None) -> List[Dict[str, Optional[str]]]:
    """Return a list of positions optionally filtered by buyer label.

    Args:
        conn: An open SQLite connection.
        buyer_label: If provided, only positions for this buyer are returned.

    Returns:
        A list of dictionaries describing each position, including buyer label,
        auction code, lot code, track_active flag and budget fields.
    """
    ensure_schema(conn)
    ensure_core_schema(conn)
    params: List = []
    query = """
        SELECT b.label AS buyer_label,
               a.auction_code AS auction_code,
               l.lot_code AS lot_code,
               p.track_active,
               p.max_budget_total_eur,
               p.my_highest_bid_eur,
               l.title AS lot_title,
               l.state AS lot_state,
               l.current_bid_eur
        FROM my_lot_positions p
        JOIN buyers b ON p.buyer_id = b.id
        JOIN lots l ON p.lot_id = l.id
        JOIN auctions a ON l.auction_id = a.id
    """
    if buyer_label:
        query += " WHERE b.label = ?"
        params.append(buyer_label)
    query += " ORDER BY a.auction_code, l.lot_code"
    cur = conn.execute(query, tuple(params))
    columns = [c[0] for c in cur.description]
    return [dict(zip(columns, row)) for row in cur.fetchall()]

def delete_position(conn: sqlite3.Connection, buyer_label: str, lot_code: str, auction_code: Optional[str] = None) -> None:
    """Remove a tracked position for a buyer and lot.

    Args:
        conn: An open SQLite connection.
        buyer_label: The label of the buyer.
        lot_code: The code of the lot.
        auction_code: Optional auction code to disambiguate lots.
    """
    ensure_schema(conn)
    buyer_id = _get_buyer_id(conn, buyer_label)
    if buyer_id is None:
        raise ValueError(f"Buyer with label '{buyer_label}' does not exist")
    lot_id = _get_lot_id(conn, lot_code, auction_code)
    if lot_id is None:
        raise ValueError(f"Lot with code '{lot_code}' not found (auction: {auction_code})")
    conn.execute(
        "DELETE FROM my_lot_positions WHERE buyer_id = ? AND lot_id = ?",
        (buyer_id, lot_id),
    )
    conn.commit()
"""Debug utilities for Troostwatch.

This module provides helper functions to inspect the state of the SQLite
database used by Troostwatch. It offers simple statistics (row counts per
table), integrity checks and the ability to view rows from a given table.
"""

from __future__ import annotations

import sqlite3
from typing import Any


def db_stats(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return a list of dictionaries describing row counts per table."""
    cur = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    )
    tables = [row[0] for row in cur.fetchall()]
    stats: list[dict[str, Any]] = []
    for table in tables:
        cur2 = conn.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur2.fetchone()[0]
        stats.append({"table": table, "rows": count})
    return stats


def db_integrity(conn: sqlite3.Connection) -> list[str]:
    """Run the SQLite integrity_check pragma and return any reported issues."""
    cur = conn.execute("PRAGMA integrity_check")
    return [row[0] for row in cur.fetchall()]


def db_view(
    conn: sqlite3.Connection, table: str, limit: int = 10
) -> list[dict[str, Any]]:
    """Fetch up to ``limit`` rows from the specified table."""
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    )
    if cur.fetchone() is None:
        raise ValueError(f"Table '{table}' does not exist in the database")
    cur = conn.execute(f"SELECT * FROM {table} LIMIT ?", (limit,))
    columns = [desc[0] for desc in cur.description]
    return [dict(zip(columns, row)) for row in cur.fetchall()]


__all__ = ["db_stats", "db_integrity", "db_view"]

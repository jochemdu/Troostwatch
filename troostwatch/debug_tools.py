"""Debug utilities for Troostwatch.

This module provides helper functions to inspect the state of the SQLite
database used by Troostwatch. It offers simple statistics (row counts per
table), integrity checks and the ability to view rows from a given table.

These functions are intended to be used by the ``troostwatch.interfaces.cli.debug``
command but can be imported and used independently in scripts or tests.
"""

from __future__ import annotations

import sqlite3
from typing import List, Dict, Any


def db_stats(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Return a list of dictionaries describing row counts per table.

    Args:
        conn: An open SQLite connection.

    Returns:
        A list of dictionaries with keys ``table`` and ``rows``.
    """
    # Query sqlite_master for all user tables (excluding sqlite internal tables)
    cur = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    )
    tables = [row[0] for row in cur.fetchall()]
    stats: List[Dict[str, Any]] = []
    for table in tables:
        cur2 = conn.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur2.fetchone()[0]
        stats.append({"table": table, "rows": count})
    return stats


def db_integrity(conn: sqlite3.Connection) -> List[str]:
    """Run the SQLite integrity_check pragma and return any reported issues.

    Args:
        conn: An open SQLite connection.

    Returns:
        A list of messages returned by ``PRAGMA integrity_check``. If the database
        is healthy, the list contains a single entry ``'ok'``.
    """
    cur = conn.execute("PRAGMA integrity_check")
    return [row[0] for row in cur.fetchall()]


def db_view(conn: sqlite3.Connection, table: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Fetch up to ``limit`` rows from the specified table.

    Args:
        conn: An open SQLite connection.
        table: The name of the table to inspect.
        limit: Maximum number of rows to return.

    Returns:
        A list of dictionaries where each key corresponds to a column name.
    """
    # Protect against SQL injection by quoting the table name using sqlite master
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    )
    if cur.fetchone() is None:
        raise ValueError(f"Table '{table}' does not exist in the database")
    cur = conn.execute(f"SELECT * FROM {table} LIMIT ?", (limit,))
    columns = [desc[0] for desc in cur.description]
    return [dict(zip(columns, row)) for row in cur.fetchall()]
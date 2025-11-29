"""Base repository class with shared database query helpers.

This module provides a base class for all repository implementations,
eliminating duplicate cursor→dict conversion logic.
"""

from __future__ import annotations

import sqlite3
from typing import Any


class BaseRepository:
    """Base class for all repository implementations.

    Provides shared helper methods for executing queries and converting
    results to dictionaries, eliminating ~80 LOC of duplicate code across
    the repository layer.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        """Initialize repository with a database connection.

        Args:
            conn: SQLite database connection
        """
        self.conn = conn

    def _fetch_all_as_dicts(
        self, query: str, params: tuple[Any, ...] | None = None
    ) -> list[dict[str, Any]]:
        """Execute query and return all rows as dictionaries.

        Args:
            query: SQL query string
            params: Query parameters (optional)

        Returns:
            List of dictionaries with column names as keys

        Example:
            >>> rows = self._fetch_all_as_dicts(
            ...     "SELECT id, name FROM users WHERE age > ?",
            ...     (18,)
            ... )
            >>> rows[0]['name']
            'Alice'
        """
        cur = self.conn.execute(query, params or ())
        columns = [c[0] for c in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]

    def _fetch_one_as_dict(
        self, query: str, params: tuple[Any, ...] | None = None
    ) -> dict[str, Any | None]:
        """Execute query and return first row as dictionary.

        Args:
            query: SQL query string
            params: Query parameters (optional)

        Returns:
            Dictionary with column names as keys, or None if no rows

        Example:
            >>> user = self._fetch_one_as_dict(
            ...     "SELECT id, name FROM users WHERE id = ?",
            ...     (42,)
            ... )
            >>> user['name'] if user else 'Not found'
            'Alice'
        """
        cur = self.conn.execute(query, params or ())
        row = cur.fetchone()
        if not row:
            return None
        columns = [c[0] for c in cur.description]
        return dict(zip(columns, row))

    def _fetch_scalar(self, query: str, params: tuple[Any, ...] | None = None) -> Any:
        """Execute query and return first column of first row.

        Args:
            query: SQL query string
            params: Query parameters (optional)

        Returns:
            Value of first column, or None if no rows

        Example:
            >>> count = self._fetch_scalar("SELECT COUNT(*) FROM users")
            >>> count
            42
        """
        cur = self.conn.execute(query, params or ())
        row = cur.fetchone()
        return row[0] if row else None

    def _execute_insert(self, query: str, params: tuple[Any, ... | None] = None) -> int:
        """Execute INSERT query and return last row ID.

        Args:
            query: SQL INSERT query string
            params: Query parameters (optional)

        Returns:
            ID of the inserted row (lastrowid)

        Example:
            >>> user_id = self._execute_insert(
            ...     "INSERT INTO users (name, age) VALUES (?, ?)",
            ...     ('Alice', 25)
            ... )
            >>> user_id
            42
        """
        cur = self.conn.execute(query, params or ())
        return cur.lastrowid or 0

    def _execute(
        self, query: str, params: tuple[Any, ... | None] = None
    ) -> sqlite3.Cursor:
        """Execute query and return cursor for custom processing.

        Use this when you need direct access to the cursor for
        custom result processing or when other helper methods
        don't fit your use case.

        Args:
            query: SQL query string
            params: Query parameters (optional)

        Returns:
            Database cursor

        Example:
            >>> cur = self._execute("UPDATE users SET active = ? WHERE id = ?", (True, 42))
            >>> cur.rowcount
            1
        """
        return self.conn.execute(query, params or ())

"""Base service class with shared connection and infrastructure patterns.

This module provides a base class for service layer implementations,
standardizing connection management, logging, and schema initialization.
"""

from __future__ import annotations

import sqlite3
from contextlib import AbstractContextManager
from typing import Callable, TypeVar

from troostwatch.infrastructure.db import ensure_schema, get_connection
from troostwatch.infrastructure.observability import get_logger

ConnectionFactory = Callable[[], AbstractContextManager[sqlite3.Connection]]
T = TypeVar("T")


class BaseService:
    """Base class for all service layer implementations.

    Provides shared infrastructure for:
    - Connection factory pattern (dependency injection for testing)
    - Automatic schema initialization
    - Consistent logging setup

    Example usage:
        class MyService(BaseService):
            def do_something(self) -> str:
                return self._with_connection(lambda conn: conn.execute("..."))

        # Production usage:
        service = MyService.from_sqlite_path("/path/to/db.sqlite")

        # Test usage with mock:
        service = MyService(mock_connection_factory)
    """

    def __init__(self, connection_factory: ConnectionFactory) -> None:
        """Initialize service with a connection factory.

        Args:
            connection_factory: Callable returning a context manager that yields
                               a sqlite3.Connection
        """
        self._connection_factory = connection_factory
        self._logger = get_logger(self.__class__.__module__)

    @classmethod
    def from_sqlite_path(cls, db_path: str) -> "BaseService":
        """Create a service bound to a SQLite database path.

        This is the standard factory method for production usage.

        Args:
            db_path: Path to the SQLite database file

        Returns:
            Service instance configured to use the specified database
        """

        def connection_factory() -> AbstractContextManager[sqlite3.Connection]:
            return get_connection(db_path)

        return cls(connection_factory)

    def _with_connection(self, fn: Callable[[sqlite3.Connection], T]) -> T:
        """Execute a function within a database connection context.

        Automatically ensures the schema is initialized before executing
        the provided function.

        Args:
            fn: Function that takes a connection and returns a result

        Returns:
            The result of the provided function

        Example:
            def get_count(self) -> int:
                return self._with_connection(
                    lambda conn: conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
                )
        """
        with self._connection_factory() as conn:
            ensure_schema(conn)
            return fn(conn)

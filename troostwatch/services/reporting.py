"""High-level reporting use cases for the CLI and APIs."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from contextlib import AbstractContextManager

from troostwatch.domain.analytics.summary import BuyerSummary
from troostwatch.infrastructure.db import ensure_schema, get_connection
from troostwatch.infrastructure.db.repositories import (BuyerRepository,
                                                        PositionRepository)
from troostwatch.infrastructure.observability import get_logger

ConnectionFactory = Callable[[], AbstractContextManager[sqlite3.Connection]]


class ReportingService:
    """Service exposing reporting and analytics operations."""

    def __init__(self, connection_factory: ConnectionFactory) -> None:
        self._connection_factory = connection_factory
        self._logger = get_logger(__name__)

    @classmethod
    def from_sqlite_path(cls, db_path: str) -> "ReportingService":
        """Create a reporting service bound to a SQLite database path."""

        def connection_factory() -> AbstractContextManager[sqlite3.Connection]:
            return get_connection(db_path)

        return cls(connection_factory)

    def get_buyer_summary(self, buyer_label: str) -> BuyerSummary:
        """Compute a summary of tracked and won lots for a buyer."""
        self._logger.debug("Computing buyer summary for %s", buyer_label)

        with self._connection_factory() as conn:
            ensure_schema(conn)
            buyer_repo = BuyerRepository(conn)
            buyer_id = buyer_repo.get_id(buyer_label)
            if buyer_id is None:
                self._logger.debug(
                    "Buyer %s not found, returning empty summary", buyer_label
                )
                return BuyerSummary()

            position_repo = PositionRepository(conn, buyers=buyer_repo)
            positions = position_repo.list(buyer_label)

        self._logger.debug(
            "Found %d positions for buyer %s", len(positions), buyer_label
        )
        return BuyerSummary.from_positions(positions)

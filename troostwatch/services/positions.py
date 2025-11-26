"""Service helpers for managing tracked lot positions."""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Callable, Dict, List, Optional

from troostwatch.infrastructure.db import ensure_schema, get_connection
from troostwatch.infrastructure.db.repositories import PositionRepository

ConnectionFactory = Callable[[], AbstractContextManager]


class PositionsService:
    """Service layer for creating, listing and deleting positions."""

    def __init__(self, connection_factory: ConnectionFactory) -> None:
        self._connection_factory = connection_factory

    @classmethod
    def from_sqlite_path(cls, db_path: str) -> "PositionsService":
        """Build a service bound to a SQLite database path."""

        def connection_factory() -> AbstractContextManager:
            return get_connection(db_path)

        return cls(connection_factory)

    def add_position(
        self,
        *,
        buyer_label: str,
        auction_code: str,
        lot_code: str,
        track_active: bool = True,
        max_budget_total_eur: Optional[float] = None,
    ) -> None:
        """Create or update a tracked position."""

        with self._connection_factory() as conn:
            ensure_schema(conn)
            PositionRepository(conn).upsert(
                buyer_label=buyer_label,
                lot_code=lot_code,
                auction_code=auction_code,
                track_active=track_active,
                max_budget_total_eur=max_budget_total_eur,
            )

    def list_positions(self, *, buyer_label: Optional[str] = None) -> List[Dict[str, object]]:
        """List positions, optionally filtered by buyer label."""

        with self._connection_factory() as conn:
            ensure_schema(conn)
            return PositionRepository(conn).list(buyer_label=buyer_label)

    def delete_position(self, *, buyer_label: str, auction_code: str, lot_code: str) -> None:
        """Remove a tracked position."""

        with self._connection_factory() as conn:
            ensure_schema(conn)
            PositionRepository(conn).delete(
                buyer_label=buyer_label,
                lot_code=lot_code,
                auction_code=auction_code,
            )

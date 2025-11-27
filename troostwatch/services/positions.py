"""Service helpers for managing tracked lot positions."""

from __future__ import annotations

import sqlite3
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from troostwatch.infrastructure.db import ensure_schema, get_connection
from troostwatch.infrastructure.db.repositories import PositionRepository
from troostwatch.infrastructure.observability import get_logger, log_context
from troostwatch.services.dto import EventPublisher, PositionDTO, PositionUpdateDTO

_logger = get_logger(__name__)

ConnectionFactory = Callable[[], AbstractContextManager[sqlite3.Connection]]


@dataclass
class PositionUpdateData:
    """Data for updating a position."""

    buyer_label: str
    lot_code: str
    auction_code: Optional[str] = None
    max_budget_total_eur: Optional[float] = None
    preferred_bid_eur: Optional[float] = None
    watch: Optional[bool] = None


class PositionsService:
    """Service layer for creating, listing and deleting positions using DTOs."""

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
        with log_context(
            buyer=buyer_label, auction_code=auction_code, lot_code=lot_code
        ):
            _logger.info("Adding position")
            with self._connection_factory() as conn:
                ensure_schema(conn)
                PositionRepository(conn).upsert(
                    buyer_label=buyer_label,
                    lot_code=lot_code,
                    auction_code=auction_code,
                    track_active=track_active,
                    max_budget_total_eur=max_budget_total_eur,
                )
            _logger.debug("Position added successfully")

    def list_positions(
        self, *, buyer_label: Optional[str] = None
    ) -> List[PositionDTO]:
        """List positions, optionally filtered by buyer label, as DTOs."""

        with self._connection_factory() as conn:
            ensure_schema(conn)
            rows = PositionRepository(conn).list(buyer_label=buyer_label)
            return [PositionDTO(**row) for row in rows]

    def delete_position(
        self, *, buyer_label: str, auction_code: str, lot_code: str
    ) -> None:
        """Remove a tracked position."""

        with self._connection_factory() as conn:
            ensure_schema(conn)
            PositionRepository(conn).delete(
                buyer_label=buyer_label,
                lot_code=lot_code,
                auction_code=auction_code,
            )


def add_position(
    *,
    db_path: str,
    buyer_label: str,
    auction_code: str,
    lot_code: str,
    track_active: bool = True,
    max_budget_total_eur: Optional[float] = None,
    connection_factory: Optional[ConnectionFactory] = None,
) -> None:
    """Add or update a tracked position using a SQLite-backed service."""

    service = _resolve_service(db_path=db_path, connection_factory=connection_factory)
    service.add_position(
        buyer_label=buyer_label,
        auction_code=auction_code,
        lot_code=lot_code,
        track_active=track_active,
        max_budget_total_eur=max_budget_total_eur,
    )


def list_positions(
    *,
    db_path: str,
    buyer_label: Optional[str] = None,
    connection_factory: Optional[ConnectionFactory] = None,
) -> List[Dict[str, object]]:
    """Return tracked positions using a SQLite-backed service."""

    service = _resolve_service(db_path=db_path, connection_factory=connection_factory)
    return service.list_positions(buyer_label=buyer_label)


def delete_position(
    *,
    db_path: str,
    buyer_label: str,
    auction_code: str,
    lot_code: str,
    connection_factory: Optional[ConnectionFactory] = None,
) -> None:
    """Delete a tracked position using a SQLite-backed service."""

    service = _resolve_service(db_path=db_path, connection_factory=connection_factory)
    service.delete_position(buyer_label=buyer_label, auction_code=auction_code, lot_code=lot_code)


def _resolve_service(
    *, db_path: str, connection_factory: Optional[ConnectionFactory]
) -> PositionsService:
    if connection_factory is not None:
        return PositionsService(connection_factory)
    return PositionsService.from_sqlite_path(db_path)


async def upsert_positions(
    *,
    repository: "PositionRepository",
    updates: List[PositionUpdateData],
    event_publisher: Optional[EventPublisher] = None,
) -> Dict[str, object]:
    """Batch upsert positions and optionally publish events.

    Args:
        repository: A PositionRepository instance for database access.
        updates: List of PositionUpdateData objects describing updates.
        event_publisher: Optional async callable for publishing events.

    Returns:
        A dict with 'updated' count and 'positions' list of updated positions.

    Raises:
        ValueError: If a buyer or lot referenced in an update is not found.
    """
    _logger.info("Batch upserting %d positions", len(updates))
    updated_positions: List[Dict[str, object]] = []

    for update in updates:
        # The repository.upsert method will validate buyer/lot existence
        # and raise ValueError if not found
        repository.upsert(
            buyer_label=update.buyer_label,
            lot_code=update.lot_code,
            auction_code=update.auction_code,
            max_budget_total_eur=update.max_budget_total_eur,
        )
        updated_positions.append({
            "buyer_label": update.buyer_label,
            "lot_code": update.lot_code,
            "auction_code": update.auction_code,
        })

    # Publish event if publisher provided
    if event_publisher is not None:
        await event_publisher({
            "type": "positions_updated",
            "count": len(updated_positions),
            "positions": updated_positions,
        })

    _logger.info("Successfully upserted %d positions", len(updated_positions))
    return {"updated": len(updated_positions), "positions": updated_positions}

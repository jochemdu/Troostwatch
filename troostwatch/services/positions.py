"""Service helpers for managing tracked lot positions."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Callable

from troostwatch.infrastructure.db import ensure_schema, get_connection
from troostwatch.infrastructure.db.repositories import PositionRepository
from troostwatch.infrastructure.observability import get_logger, log_context
from troostwatch.services.dto import EventPublisher, PositionDTO

_logger = get_logger(__name__)

ConnectionFactory = Callable[[], AbstractContextManager[sqlite3.Connection]]


@dataclass
class PositionUpdateData:
    """Data for updating a position."""

    buyer_label: str
    lot_code: str
    auction_code: str | None = None
    max_budget_total_eur: float | None = None
    preferred_bid_eur: float | None = None
    watch: bool | None = None


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
        max_budget_total_eur: float | None = None,
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

    def list_positions(self, *, buyer_label: str | None = None) -> list[PositionDTO]:
        """List positions, optionally filtered by buyer label, as DTOs."""

        with self._connection_factory() as conn:
            ensure_schema(conn)
            rows = PositionRepository(conn).list(buyer_label=buyer_label)
            return [self._row_to_dto(row) for row in rows]

    @staticmethod
    def _row_to_dto(row: dict[str, str | None]) -> PositionDTO:
        """Convert a repository row to a PositionDTO with proper type coercion."""
        max_budget = row.get("max_budget_total_eur")
        my_highest = row.get("my_highest_bid_eur")
        current_bid = row.get("current_bid_eur")

        return PositionDTO(
            buyer_label=str(row.get("buyer_label") or ""),
            lot_code=str(row.get("lot_code") or ""),
            auction_code=row.get("auction_code"),
            track_active=bool(row.get("track_active", True)),
            max_budget_total_eur=float(max_budget) if max_budget else None,
            my_highest_bid_eur=float(my_highest) if my_highest else None,
            lot_title=row.get("lot_title"),
            lot_state=row.get("lot_state"),
            current_bid_eur=float(current_bid) if current_bid else None,
        )

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
    connection_factory: ConnectionFactory | None = None,
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
    connection_factory: ConnectionFactory | None = None,
) -> list[PositionDTO]:
    """Return tracked positions using a SQLite-backed service."""

    service = _resolve_service(db_path=db_path, connection_factory=connection_factory)
    return service.list_positions(buyer_label=buyer_label)


def delete_position(
    *,
    db_path: str,
    buyer_label: str,
    auction_code: str,
    connection_factory: ConnectionFactory | None = None,
) -> None:
    """Delete a tracked position using a SQLite-backed service."""

    service = _resolve_service(db_path=db_path, connection_factory=connection_factory)
    service.delete_position(
        buyer_label=buyer_label, auction_code=auction_code, lot_code=lot_code
    )


def _resolve_service(
    *, db_path: str, connection_factory: ConnectionFactory | None
) -> PositionsService:
    if connection_factory is not None:
        return PositionsService(connection_factory)
    return PositionsService.from_sqlite_path(db_path)


async def upsert_positions(
    *,
    repository: "PositionRepository",
    updates: list[PositionUpdateData],
    event_publisher: EventPublisher | None = None,
) -> dict[str, object]:
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
    updated_positions: list[dict[str, object]] = []

    for update in updates:
        # The repository.upsert method will validate buyer/lot existence
        # and raise ValueError if not found
        repository.upsert(
            buyer_label=update.buyer_label,
            lot_code=update.lot_code,
            auction_code=update.auction_code,
            max_budget_total_eur=update.max_budget_total_eur,
        )
        updated_positions.append(
            {
                "buyer_label": update.buyer_label,
                "lot_code": update.lot_code,
                "auction_code": update.auction_code,
            }
        )

    # Publish event if publisher provided
    if event_publisher is not None:
        await event_publisher(
            {
                "type": "positions_updated",
                "count": len(updated_positions),
                "positions": updated_positions,
            }
        )

    _logger.info("Successfully upserted %d positions", len(updated_positions))
    return {"updated": len(updated_positions), "positions": updated_positions}

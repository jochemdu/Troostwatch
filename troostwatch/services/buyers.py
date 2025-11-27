from __future__ import annotations

from typing import Any, Optional

from troostwatch.infrastructure.db.repositories import BuyerRepository
from troostwatch.infrastructure.db.repositories.buyers import DuplicateBuyerError
from troostwatch.infrastructure.observability import get_logger
from troostwatch.services.dto import BuyerDTO, BuyerCreateDTO, EventPublisher

_logger = get_logger(__name__)


class BuyerAlreadyExistsError(Exception):
    """Raised when attempting to create a buyer with a duplicate label."""


def _row_to_dto(row: dict[str, Any]) -> BuyerDTO:
    """Convert a database row to a BuyerDTO with proper type coercion."""
    return BuyerDTO(
        id=int(row["id"]),
        label=str(row["label"]),
        name=str(row["name"]) if row.get("name") else None,
        notes=str(row["notes"]) if row.get("notes") else None,
    )


class BuyerService:
    """Service layer for managing buyers and emitting related events using DTOs."""

    def __init__(
        self, repository: BuyerRepository, event_publisher: EventPublisher | None = None
    ) -> None:
        self._repository = repository
        self._event_publisher = event_publisher

    def list_buyers(self) -> list[BuyerDTO]:
        buyers = self._repository.list()
        _logger.debug("Listed %d buyers", len(buyers))
        return [_row_to_dto(buyer) for buyer in buyers]

    async def create_buyer(
        self,
        *,
        label: str,
        name: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> BuyerCreateDTO:
        _logger.info("Creating buyer: %s", label)
        try:
            self._repository.add(label, name, notes)
        except DuplicateBuyerError as exc:
            _logger.warning("Buyer already exists: %s", label)
            raise BuyerAlreadyExistsError(str(exc)) from exc

        payload = BuyerCreateDTO(label=label, name=name, notes=notes)
        await self._publish_event({"type": "buyer_created", "label": label})
        _logger.info("Buyer created successfully: %s", label)
        return payload

    async def delete_buyer(self, *, label: str) -> None:
        _logger.info("Deleting buyer: %s", label)
        self._repository.delete(label)
        await self._publish_event({"type": "buyer_deleted", "label": label})
        _logger.info("Buyer deleted: %s", label)

    async def _publish_event(self, payload: dict[str, object]) -> None:
        if self._event_publisher is None:
            return
        await self._event_publisher(payload)


def list_buyers(repository: BuyerRepository) -> list[BuyerDTO]:
    return BuyerService(repository).list_buyers()


async def create_buyer(
    *,
    repository: BuyerRepository,
    label: str,
    name: Optional[str] = None,
    notes: Optional[str] = None,
    event_publisher: EventPublisher | None = None,
) -> BuyerCreateDTO:
    service = BuyerService(repository, event_publisher)
    return await service.create_buyer(label=label, name=name, notes=notes)


async def delete_buyer(
    *,
    repository: BuyerRepository,
    label: str,
    event_publisher: EventPublisher | None = None,
) -> None:
    service = BuyerService(repository, event_publisher)
    await service.delete_buyer(label=label)

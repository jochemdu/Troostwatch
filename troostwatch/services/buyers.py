from __future__ import annotations

from typing import Awaitable, Callable, Optional

from troostwatch.infrastructure.db.repositories import BuyerRepository
from troostwatch.infrastructure.db.repositories.buyers import DuplicateBuyerError
from troostwatch.infrastructure.observability import get_logger

_logger = get_logger(__name__)

EventPublisher = Callable[[dict[str, object]], Awaitable[None]]


class BuyerAlreadyExistsError(Exception):
    """Raised when attempting to create a buyer with a duplicate label."""


class BuyerService:
    """Service layer for managing buyers and emitting related events."""

    def __init__(
        self, repository: BuyerRepository, event_publisher: EventPublisher | None = None
    ) -> None:
        self._repository = repository
        self._event_publisher = event_publisher

    def list_buyers(self) -> list[dict[str, int | str | None]]:
        buyers = self._repository.list()
        _logger.debug("Listed %d buyers", len(buyers))
        return buyers

    async def create_buyer(
        self,
        *,
        label: str,
        name: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> dict[str, str]:
        _logger.info("Creating buyer: %s", label)
        try:
            self._repository.add(label, name, notes)
        except DuplicateBuyerError as exc:
            _logger.warning("Buyer already exists: %s", label)
            raise BuyerAlreadyExistsError(str(exc)) from exc

        payload = {"status": "created", "label": label}
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


def list_buyers(repository: BuyerRepository) -> list[dict[str, int | str | None]]:
    return BuyerService(repository).list_buyers()


async def create_buyer(
    *,
    repository: BuyerRepository,
    label: str,
    name: Optional[str] = None,
    notes: Optional[str] = None,
    event_publisher: EventPublisher | None = None,
) -> dict[str, str]:
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

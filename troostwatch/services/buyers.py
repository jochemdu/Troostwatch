from __future__ import annotations

from typing import Awaitable, Callable, Optional

from troostwatch.infrastructure.db.repositories import BuyerRepository
from troostwatch.infrastructure.db.repositories.buyers import DuplicateBuyerError

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
        return self._repository.list()

    async def create_buyer(
        self,
        *,
        label: str,
        name: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> dict[str, str]:
        try:
            self._repository.add(label, name, notes)
        except DuplicateBuyerError as exc:
            raise BuyerAlreadyExistsError(str(exc)) from exc

        payload = {"status": "created", "label": label}
        await self._publish_event({"type": "buyer_created", "label": label})
        return payload

    async def delete_buyer(self, *, label: str) -> None:
        self._repository.delete(label)
        await self._publish_event({"type": "buyer_deleted", "label": label})

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

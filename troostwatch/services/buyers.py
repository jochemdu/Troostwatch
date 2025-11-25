from __future__ import annotations

from typing import Awaitable, Callable, Optional

from troostwatch.infrastructure.db.repositories import BuyerRepository
from troostwatch.infrastructure.db.repositories.buyers import DuplicateBuyerError

EventPublisher = Callable[[dict[str, object]], Awaitable[None]]


def list_buyers(repository: BuyerRepository) -> list[dict[str, Optional[str]]]:
    return repository.list()


async def create_buyer(
    *,
    repository: BuyerRepository,
    label: str,
    name: Optional[str] = None,
    notes: Optional[str] = None,
    event_publisher: EventPublisher | None = None,
) -> dict[str, str]:
    try:
        repository.add(label, name, notes)
    except DuplicateBuyerError:
        # Let callers translate repository-specific errors to their boundary concerns
        raise

    payload = {"status": "created", "label": label}
    if event_publisher:
        await event_publisher({"type": "buyer_created", "label": label})
    return payload


async def delete_buyer(
    *, repository: BuyerRepository, label: str, event_publisher: EventPublisher | None = None
) -> None:
    repository.delete(label)
    if event_publisher:
        await event_publisher({"type": "buyer_deleted", "label": label})

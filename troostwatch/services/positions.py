from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Awaitable, Callable, Iterable, Optional

from troostwatch.infrastructure.db.repositories import PositionRepository

EventPublisher = Callable[[dict[str, object]], Awaitable[None]]


@dataclass
class PositionUpdateData:
    buyer_label: str
    lot_code: str
    auction_code: Optional[str] = None
    max_budget_total_eur: Optional[float] = None
    preferred_bid_eur: Optional[float] = None
    watch: Optional[bool] = None


async def upsert_positions(
    *,
    repository: PositionRepository,
    updates: Iterable[PositionUpdateData],
    event_publisher: EventPublisher | None = None,
) -> dict[str, int]:
    processed: list[dict[str, object]] = []
    for update in updates:
        repository.upsert(
            buyer_label=update.buyer_label,
            lot_code=update.lot_code,
            auction_code=update.auction_code,
            track_active=True if update.watch is None else update.watch,
            max_budget_total_eur=update.max_budget_total_eur,
            my_highest_bid_eur=update.preferred_bid_eur,
        )
        processed.append(asdict(update))

    if event_publisher:
        await event_publisher({"type": "positions_updated", "count": len(processed), "items": processed})

    return {"updated": len(processed)}

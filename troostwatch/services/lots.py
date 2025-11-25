"""Service helpers for viewing and filtering lots."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable, List, Optional

from troostwatch.infrastructure.db.repositories import LotRepository


@dataclass
class LotView:
    """DTO representing a lot summary suitable for API responses."""

    auction_code: str
    lot_code: str
    title: Optional[str]
    state: Optional[str]
    current_bid_eur: Optional[float]
    bid_count: Optional[int]
    current_bidder_label: Optional[str]
    closing_time_current: Optional[str]
    closing_time_original: Optional[str]

    @classmethod
    def from_record(cls, record: dict[str, object]) -> "LotView":
        return cls(
            auction_code=str(record["auction_code"]),
            lot_code=str(record["lot_code"]),
            title=record.get("title"),
            state=record.get("state"),
            current_bid_eur=record.get("current_bid_eur"),
            bid_count=record.get("bid_count"),
            current_bidder_label=record.get("current_bidder_label"),
            closing_time_current=record.get("closing_time_current"),
            closing_time_original=record.get("closing_time_original"),
        )

    def to_dict(self) -> dict[str, object | None]:
        return asdict(self)


class LotViewService:
    """Service exposing read-only lot views for APIs and CLIs."""

    def __init__(self, lot_repository: LotRepository) -> None:
        self._lot_repository = lot_repository

    def list_lots(
        self,
        *,
        auction_code: Optional[str] = None,
        state: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[LotView]:
        rows = self._lot_repository.list_lots(
            auction_code=auction_code,
            state=state,
            limit=limit,
        )
        return self._to_dtos(rows)

    def _to_dtos(self, rows: Iterable[dict[str, object]]) -> List[LotView]:
        return [LotView.from_record(row) for row in rows]

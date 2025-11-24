"""Domain models and helpers for analytics summaries."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Optional


@dataclass
class TrackedLotSummary:
    """Aggregate view of a tracked lot used in buyer summaries."""

    lot_code: str
    title: str
    state: str
    current_bid_eur: Optional[float]
    max_budget_total_eur: Optional[float]
    track_active: bool

    def to_dict(self) -> dict:
        return {
            "lot_code": self.lot_code,
            "title": self.title,
            "state": self.state,
            "current_bid_eur": self.current_bid_eur,
            "max_budget_total_eur": self.max_budget_total_eur,
            "track_active": self.track_active,
        }


@dataclass
class BuyerSummary:
    """High-level summary of tracked and won lots for a buyer."""

    tracked_count: int = 0
    open_count: int = 0
    closed_count: int = 0
    open_tracked_lots: List[TrackedLotSummary] = field(default_factory=list)
    won_lots: List[TrackedLotSummary] = field(default_factory=list)
    open_exposure_min_eur: float = 0.0
    open_exposure_max_eur: float = 0.0

    @classmethod
    def from_positions(cls, positions: Iterable[dict]) -> "BuyerSummary":
        summary = cls()
        rows = list(positions)
        summary.tracked_count = len(rows)

        for row in rows:
            state = row.get("lot_state")
            current_bid = row.get("current_bid_eur")
            max_budget = row.get("max_budget_total_eur")
            track_active = bool(row.get("track_active"))

            lot_summary = TrackedLotSummary(
                lot_code=row["lot_code"],
                title=row.get("lot_title") or "",
                state=state or "",
                current_bid_eur=current_bid,
                max_budget_total_eur=max_budget,
                track_active=track_active,
            )

            if state != "closed":
                summary.open_count += 1
                if track_active:
                    summary.open_tracked_lots.append(lot_summary)
                    if current_bid is not None:
                        summary.open_exposure_min_eur += float(current_bid)
                    if max_budget is not None:
                        summary.open_exposure_max_eur += float(max_budget)
                    elif current_bid is not None:
                        summary.open_exposure_max_eur += float(current_bid)
            else:
                summary.closed_count += 1
                summary.won_lots.append(lot_summary)

        return summary

    def to_dict(self) -> dict:
        return {
            "tracked_count": self.tracked_count,
            "open_count": self.open_count,
            "closed_count": self.closed_count,
            "open_tracked_lots": [lot.to_dict() for lot in self.open_tracked_lots],
            "won_lots": [lot.to_dict() for lot in self.won_lots],
            "open_exposure_min_eur": self.open_exposure_min_eur,
            "open_exposure_max_eur": self.open_exposure_max_eur,
        }

"""Lot domain model with business logic."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class LotState(str, Enum):
    """Enumeration of possible lot states."""

    SCHEDULED = "scheduled"
    RUNNING = "running"
    CLOSED = "closed"
    UNKNOWN = "unknown"

    @classmethod
    def from_string(cls, value: str | None) -> "LotState":
        """Convert a string to a LotState, defaulting to UNKNOWN."""
        if not value:
            return cls.UNKNOWN
        normalized = value.lower().strip()
        if normalized in ("scheduled", "published"):
            return cls.SCHEDULED
        if normalized in ("running", "open", "bidding_open"):
            return cls.RUNNING
        if normalized in ("closed", "ended", "bidding_closed"):
            return cls.CLOSED
        return cls.UNKNOWN


@dataclass
class Lot:
    """Domain model representing a lot in an auction.

    This model encapsulates the business logic related to lots,
    such as determining if a lot is active, calculating effective prices,
    and checking bidding eligibility.
    """

    lot_code: str
    auction_code: str
    title: str
    state: LotState = LotState.UNKNOWN
    opens_at: datetime | None = None
    closing_time_current: datetime | None = None
    closing_time_original: datetime | None = None
    opening_bid_eur: float | None = None
    current_bid_eur: float | None = None
    bid_count: int | None = None
    current_bidder_label: str | None = None
    location_city: str | None = None
    location_country: str | None = None
    url: str | None = None

    @property
    def is_active(self) -> bool:
        """Check if the lot is currently active (running or scheduled)."""
        return self.state in (LotState.RUNNING, LotState.SCHEDULED)

    @property
    def is_running(self) -> bool:
        """Check if the lot is currently accepting bids."""
        return self.state == LotState.RUNNING

    @property
    def is_closed(self) -> bool:
        """Check if the lot has ended."""
        return self.state == LotState.CLOSED

    @property
    def effective_price(self) -> float | None:
        """Return the current bid if available, otherwise the opening bid."""
        if self.current_bid_eur is not None:
            return self.current_bid_eur
        return self.opening_bid_eur

    @property
    def has_bids(self) -> bool:
        """Check if the lot has received any bids."""
        if self.bid_count is not None:
            return self.bid_count > 0
        return self.current_bid_eur is not None

    @property
    def time_extended(self) -> bool:
        """Check if the closing time has been extended from the original."""
        if self.closing_time_current is None or self.closing_time_original is None:
            return False
        return self.closing_time_current > self.closing_time_original

    @property
    def location(self) -> str | None:
        """Return the full location string."""
        parts = [p for p in [self.location_city, self.location_country] if p]
        return ", ".join(parts) if parts else None

    def can_bid(self, amount: float) -> tuple[bool, str | None]:
        """Check if a bid of the given amount would be valid.

        Returns:
            A tuple of (is_valid, error_message).
        """
        if not self.is_running:
            return False, f"Lot is not running (state: {self.state.value})"

        min_bid = self.effective_price
        if min_bid is not None and amount <= min_bid:
            return False, f"Bid must be higher than current price (€{min_bid:.2f})"

        return True, None

    @classmethod
    def from_dict(cls, data: dict) -> "Lot":
        """Create a Lot from a dictionary (e.g., from database row)."""
        state_str = data.get("state") or data.get("lot_state")

        def parse_datetime(value: object) -> datetime | None:
            if value is None:
                return None
            if isinstance(value, datetime):
                return value
            if isinstance(value, str):
                try:
                    return datetime.fromisoformat(value.replace("Z", "+00:00"))
                except ValueError:
                    return None
            return None

        return cls(
            lot_code=data.get("lot_code", ""),
            auction_code=data.get("auction_code", ""),
            title=data.get("title", ""),
            state=LotState.from_string(state_str),
            opens_at=parse_datetime(data.get("opens_at")),
            closing_time_current=parse_datetime(data.get("closing_time_current")),
            closing_time_original=parse_datetime(data.get("closing_time_original")),
            opening_bid_eur=data.get("opening_bid_eur"),
            current_bid_eur=data.get("current_bid_eur"),
            bid_count=data.get("bid_count"),
            current_bidder_label=data.get("current_bidder_label"),
            location_city=data.get("location_city"),
            location_country=data.get("location_country"),
            url=data.get("url"),
        )


__all__ = ["Lot", "LotState"]

"""
Centralized DTOs and input/output models for Troostwatch services.
"""

from __future__ import annotations
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any


# --- Event Publishing Types ---
EventPayload = dict[str, object]
EventPublisher = Callable[[EventPayload], Awaitable[None]]


async def noop_event_publisher(_: EventPayload) -> None:
    """Default no-op event publisher for services that don't need events."""


# --- Lot DTOs ---
@dataclass
class LotViewDTO:
    auction_code: str
    lot_code: str
    title: str | None = None
    state: str | None = None
    current_bid_eur: float | None = None
    bid_count: int | None = None
    current_bidder_label: str | None = None
    closing_time_current: str | None = None
    closing_time_original: str | None = None
    brand: str | None = None
    is_active: bool = False
    effective_price: float | None = None


@dataclass
class LotInputDTO:
    auction_code: str
    lot_code: str
    title: str
    url: str | None = None
    state: str | None = None
    opens_at: str | None = None
    closing_time: str | None = None
    bid_count: int | None = None
    opening_bid_eur: float | None = None
    current_bid_eur: float | None = None
    location_city: str | None = None
    location_country: str | None = None
    auction_title: str | None = None
    auction_url: str | None = None


# --- Buyer DTOs ---
@dataclass
class BuyerDTO:
    id: int
    label: str
    name: str | None = None
    notes: str | None = None


@dataclass
class BuyerCreateDTO:
    label: str
    name: str | None = None
    notes: str | None = None


# --- Position DTOs ---
@dataclass
class PositionDTO:
    buyer_label: str
    lot_code: str
    auction_code: str | None = None
    track_active: bool = True
    max_budget_total_eur: float | None = None
    my_highest_bid_eur: float | None = None
    lot_title: str | None = None
    lot_state: str | None = None
    current_bid_eur: float | None = None


@dataclass
class PositionUpdateDTO:
    buyer_label: str
    lot_code: str
    auction_code: str | None = None
    max_budget_total_eur: float | None = None
    preferred_bid_eur: float | None = None
    watch: bool | None = None


# --- Bid DTOs ---
@dataclass
class BidDTO:
    id: int
    buyer_label: str
    lot_code: str
    auction_code: str
    amount_eur: float
    placed_at: str
    lot_title: str | None = None
    note: str | None = None


@dataclass
class BidCreateDTO:
    buyer_label: str
    auction_code: str
    lot_code: str
    amount_eur: float
    note: str | None = None


# --- Bid Result ---
@dataclass
class BidResultDTO:
    """Structured response from a bid submission."""

    lot_code: str
    auction_code: str
    amount_eur: float
    raw_response: dict[str, Any]

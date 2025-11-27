"""
Centralized DTOs and input/output models for Troostwatch services.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

# --- Lot DTOs ---
@dataclass
class LotViewDTO:
    auction_code: str
    lot_code: str
    title: Optional[str] = None
    state: Optional[str] = None
    current_bid_eur: Optional[float] = None
    bid_count: Optional[int] = None
    current_bidder_label: Optional[str] = None
    closing_time_current: Optional[str] = None
    closing_time_original: Optional[str] = None
    brand: Optional[str] = None
    is_active: bool = False
    effective_price: Optional[float] = None

@dataclass
class LotInputDTO:
    auction_code: str
    lot_code: str
    title: str
    url: Optional[str] = None
    state: Optional[str] = None
    opens_at: Optional[str] = None
    closing_time: Optional[str] = None
    bid_count: Optional[int] = None
    opening_bid_eur: Optional[float] = None
    current_bid_eur: Optional[float] = None
    location_city: Optional[str] = None
    location_country: Optional[str] = None
    auction_title: Optional[str] = None
    auction_url: Optional[str] = None

# --- Buyer DTOs ---
@dataclass
class BuyerDTO:
    id: int
    label: str
    name: Optional[str] = None
    notes: Optional[str] = None

@dataclass
class BuyerCreateDTO:
    label: str
    name: Optional[str] = None
    notes: Optional[str] = None

# --- Position DTOs ---
@dataclass
class PositionDTO:
    id: int
    buyer_label: str
    lot_code: str
    auction_code: Optional[str] = None
    max_budget_total_eur: Optional[float] = None
    preferred_bid_eur: Optional[float] = None
    track_active: bool = True
    lot_title: Optional[str] = None
    current_bid_eur: Optional[float] = None
    closing_time: Optional[str] = None

@dataclass
class PositionUpdateDTO:
    buyer_label: str
    lot_code: str
    auction_code: Optional[str] = None
    max_budget_total_eur: Optional[float] = None
    preferred_bid_eur: Optional[float] = None
    watch: Optional[bool] = None

# --- Bid DTOs ---
@dataclass
class BidDTO:
    id: int
    buyer_label: str
    lot_code: str
    auction_code: str
    amount_eur: float
    placed_at: str
    lot_title: Optional[str] = None
    note: Optional[str] = None

@dataclass
class BidCreateDTO:
    buyer_label: str
    auction_code: str
    lot_code: str
    amount_eur: float
    note: Optional[str] = None

# --- Sync DTOs ---
@dataclass
class SyncRunResultDTO:
    run_id: Optional[int]
    status: str
    pages_scanned: int = 0
    lots_scanned: int = 0
    lots_updated: int = 0
    error_count: int = 0
    errors: List[str] = None

@dataclass
class SyncSummaryDTO:
    status: str
    auction_code: Optional[str] = None
    result: Optional[SyncRunResultDTO] = None
    error: Optional[str] = None

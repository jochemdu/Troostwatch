"""FastAPI application exposing Troostwatch repositories.

Run with ``uvicorn troostwatch.app.api:app``.
"""

from __future__ import annotations

import asyncio
from typing import Annotated, Any, cast

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from troostwatch import __version__
from troostwatch.app.dependencies import (
    # Annotated dependency types (modern FastAPI pattern)
    LotRepositoryDep,
    BuyerRepositoryDep,
    PositionRepositoryDep,
    AuctionRepositoryDep,
    BidRepositoryDep,
)
from troostwatch.services import positions as position_service
from troostwatch.services.buyers import BuyerAlreadyExistsError, BuyerService
from troostwatch.services.lots import (
    LotInput,
    LotManagementService,
    LotView,
    LotViewService,
)
from troostwatch.services.reporting import ReportingService
from troostwatch.services.sync_service import SyncService
from troostwatch.services.dto import BuyerCreateDTO
from troostwatch.services.positions import PositionUpdateData


class LotEventBus:
    """Simple in-memory broadcaster for lot updates."""

    def __init__(self) -> None:
        self._subscribers: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def subscribe(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._subscribers.add(websocket)

    async def unsubscribe(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._subscribers.discard(websocket)

    async def publish(self, payload: dict[str, Any]) -> None:
        stale: list[WebSocket] = []
        async with self._lock:
            subscribers = list(self._subscribers)
        for subscriber in subscribers:
            try:
                await subscriber.send_json(payload)
            except WebSocketDisconnect:
                stale.append(subscriber)
            except Exception:
                stale.append(subscriber)
        for subscriber in stale:
            await self.unsubscribe(subscriber)


event_bus = LotEventBus()
sync_service = SyncService(event_publisher=event_bus.publish)
app = FastAPI(title="Troostwatch API", version=__version__)

# Enable CORS for local development (UI on port 3000, API on port 8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """API root endpoint with welcome message and links."""
    return {
        "name": "Troostwatch API",
        "version": __version__,
        "docs": "/docs",
        "redoc": "/redoc",
        "endpoints": {
            "lots": "/lots",
            "buyers": "/buyers",
            "sync": "/sync",
            "live_sync_status": "/live-sync/status",
            "websocket": "/ws/lots",
        },
    }


def get_buyer_service(
    repository: BuyerRepositoryDep,
) -> BuyerService:
    return BuyerService(repository=repository, event_publisher=event_bus.publish)


def get_lot_view_service(
    lot_repository: LotRepositoryDep,
) -> LotViewService:
    return LotViewService(lot_repository)


def get_sync_service() -> SyncService:
    return sync_service


# Annotated service dependency types
BuyerServiceDep = Annotated[BuyerService, Depends(get_buyer_service)]
LotViewServiceDep = Annotated[LotViewService, Depends(get_lot_view_service)]
SyncServiceDep = Annotated[SyncService, Depends(get_sync_service)]


class BuyerCreateRequest(BaseModel):
    label: str
    name: str | None = None
    notes: str | None = None
    name: str | None = None
    notes: str | None = None


class BuyerResponse(BaseModel):
    id: int
    label: str
    name: str | None = None
    notes: str | None = None
    name: str | None = None
    notes: str | None = None


class BuyerCreateResponse(BaseModel):
    status: str
    label: str


class PositionUpdate(BaseModel):
    buyer_label: str
    lot_code: str
    auction_code: str | None = None
    max_budget_total_eur: float | None = Field(None, ge=0)
    preferred_bid_eur: float | None = Field(None, ge=0)
    watch: bool | None = None
    auction_code: str | None = None
    max_budget_total_eur: float | None = Field(None, ge=0)
    preferred_bid_eur: float | None = Field(None, ge=0)
    watch: bool | None = None


class PositionResponse(BaseModel):
    """A tracked position linking a buyer to a lot."""

    buyer_label: str
    lot_code: str
    auction_code: str | None = None
    track_active: bool = True
    max_budget_total_eur: float | None = None
    my_highest_bid_eur: float | None = None
    lot_title: str | None = None
    lot_state: str | None = None
    current_bid_eur: float | None = None
    max_budget_total_eur: float | None = None
    my_highest_bid_eur: float | None = None
    lot_title: str | None = None
    lot_state: str | None = None
    current_bid_eur: float | None = None


class PositionBatchRequest(BaseModel):
    updates: list[PositionUpdate]


class PositionBatchResponse(BaseModel):
    """Response for batch position updates."""

    updated: int
    created: int = 0
    errors: list[str] = Field(default_factory=list)


class SyncRequest(BaseModel):
    auction_code: str
    auction_url: str
    max_pages: int | None = Field(None, ge=1)
    dry_run: bool = False


class SyncRunResultResponse(BaseModel):
    """Result of a single sync run."""

    run_id: int | None = None
    status: str  # 'success', 'failed', 'running'
    pages_scanned: int = 0
    lots_scanned: int = 0
    lots_updated: int = 0
    error_count: int = 0
    errors: list[str] = Field(default_factory=list)


class SyncSummaryResponse(BaseModel):
    """Summary response for a sync operation."""

    status: str  # 'success', 'failed', 'error'
    auction_code: str | None = None
    result: SyncRunResultResponse | None = None
    error: str | None = None
    auction_code: str | None = None
    result: SyncRunResultResponse | None = None
    error: str | None = None


class LiveSyncStatusResponse(BaseModel):
    """Status of the live sync worker."""

    state: str  # 'idle', 'running', 'paused', 'stopping'
    last_sync: str | None = None
    next_sync: str | None = None
    current_auction: str | None = None
    last_sync: str | None = None
    next_sync: str | None = None
    current_auction: str | None = None


class LiveSyncControlResponse(BaseModel):
    """Response for live sync control actions."""

    state: str
    detail: str | None = None


class LiveSyncStartRequest(BaseModel):
    auction_code: str
    auction_url: str
    max_pages: int | None = Field(None, ge=1)
    dry_run: bool = False
    interval_seconds: float | None = Field(
        None,
        ge=0,
        description="Seconds between sync runs; defaults to configured worker interval.",
    )


class BidResponse(BaseModel):
    """A recorded bid."""

    id: int
    buyer_label: str
    lot_code: str
    auction_code: str
    lot_title: str | None = None
    amount_eur: float
    placed_at: str
    note: str | None = None


class BidCreateRequest(BaseModel):
    """Request to record a new bid."""

    buyer_label: str
    auction_code: str
    lot_code: str
    amount_eur: float = Field(gt=0)
    note: str | None = None


class TrackedLotSummaryResponse(BaseModel):
    """Summary of a tracked lot in buyer report."""

    lot_code: str
    title: str
    state: str
    current_bid_eur: float | None = None
    max_budget_total_eur: float | None = None
    current_bid_eur: float | None = None
    max_budget_total_eur: float | None = None
    track_active: bool = True


class BuyerSummaryResponse(BaseModel):
    """Buyer exposure and position summary."""

    buyer_label: str
    tracked_count: int = 0
    open_count: int = 0
    closed_count: int = 0
    open_exposure_min_eur: float = 0.0
    open_exposure_max_eur: float = 0.0
    open_tracked_lots: list[TrackedLotSummaryResponse] = Field(default_factory=list)
    won_lots: list[TrackedLotSummaryResponse] = Field(default_factory=list)
    open_tracked_lots: list[TrackedLotSummaryResponse] = Field(default_factory=list)
    won_lots: list[TrackedLotSummaryResponse] = Field(default_factory=list)


class AuctionResponse(BaseModel):
    """Auction summary."""

    auction_code: str
    title: str | None = None
    url: str | None = None
    starts_at: str | None = None
    ends_at_planned: str | None = None
    title: str | None = None
    url: str | None = None
    starts_at: str | None = None
    ends_at_planned: str | None = None
    active_lots: int = 0
    lot_count: int = 0


class LotCreateRequest(BaseModel):
    """Request to manually add or update a lot."""

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


class LotUpdateRequest(BaseModel):
    """Request to update lot fields (notes, ean)."""

    notes: str | None = None
    ean: str | None = None
    notes: str | None = None
    ean: str | None = None


class LotSpecResponse(BaseModel):
    """A specification key-value pair for a lot."""

    id: int
    parent_id: int | None = None
    template_id: int | None = None
    parent_id: int | None = None
    template_id: int | None = None
    key: str
    value: str | None = None
    ean: str | None = None
    price_eur: float | None = None
    release_date: str | None = None
    category: str | None = None
    value: str | None = None
    ean: str | None = None
    price_eur: float | None = None
    release_date: str | None = None
    category: str | None = None


class ReferencePriceResponse(BaseModel):
    """A reference price for a lot."""

    id: int
    condition: str  # 'new', 'used', 'refurbished'
    price_eur: float
    source: str | None = None
    url: str | None = None
    notes: str | None = None
    created_at: str | None = None
    source: str | None = None
    url: str | None = None
    notes: str | None = None
    created_at: str | None = None


class ReferencePriceCreateRequest(BaseModel):
    """Request to add a reference price."""

    condition: str = Field(default="used", pattern="^(new|used|refurbished)$")
    price_eur: float = Field(ge=0)
    source: str | None = None
    url: str | None = None
    notes: str | None = None
    source: str | None = None
    url: str | None = None
    notes: str | None = None


class ReferencePriceUpdateRequest(BaseModel):
    """Request to update a reference price."""

    condition: str | None = Field(None, pattern="^(new|used|refurbished)$")
    price_eur: float | None = Field(None, ge=0)
    source: str | None = None
    url: str | None = None
    notes: str | None = None
    condition: str | None = Field(None, pattern="^(new|used|refurbished)$")
    price_eur: float | None = Field(None, ge=0)
    source: str | None = None
    url: str | None = None
    notes: str | None = None


class LotDetailResponse(BaseModel):
    """Detailed lot information including specs and reference prices."""

    auction_code: str
    lot_code: str
    title: str | None = None
    url: str | None = None
    state: str | None = None
    current_bid_eur: float | None = None
    bid_count: int | None = None
    opening_bid_eur: float | None = None
    closing_time_current: str | None = None
    closing_time_original: str | None = None
    brand: str | None = None
    ean: str | None = None
    location_city: str | None = None
    location_country: str | None = None
    notes: str | None = None
    specs: list[LotSpecResponse] = Field(default_factory=list)
    reference_prices: list[ReferencePriceResponse] = Field(default_factory=list)
    title: str | None = None
    url: str | None = None
    state: str | None = None
    current_bid_eur: float | None = None
    bid_count: int | None = None
    opening_bid_eur: float | None = None
    closing_time_current: str | None = None
    closing_time_original: str | None = None
    brand: str | None = None
    ean: str | None = None
    location_city: str | None = None
    location_country: str | None = None
    notes: str | None = None
    specs: list[LotSpecResponse] = Field(default_factory=list)
    reference_prices: list[ReferencePriceResponse] = Field(default_factory=list)


class LotCreateResponse(BaseModel):
    """Response after creating/updating a lot."""

    status: str
    lot_code: str
    auction_code: str


@app.get("/lots", response_model=list[LotView])
async def list_lots(
    lot_view_service: LotViewServiceDep,
    auction_code: str | None = None,
    state: str | None = None,
    brand: str | None = None,
    limit: int | None = Query(100, ge=1, le=1000),
) -> list[LotView]:
    lots = lot_view_service.list_lots(
        auction_code=auction_code, state=state, brand=brand, limit=limit
    )
    return [
        LotView(
            auction_code=lot.auction_code,
            lot_code=lot.lot_code,
            title=lot.title,
            state=lot.state,
            current_bid_eur=lot.current_bid_eur,
            bid_count=lot.bid_count,
            current_bidder_label=lot.current_bidder_label,
            closing_time_current=lot.closing_time_current,
            closing_time_original=lot.closing_time_original,
            brand=lot.brand,
            is_active=lot.is_active,
            effective_price=lot.effective_price,
        )
        for lot in lots
    ]


class SearchResultResponse(BaseModel):
    """A search result with lot details and match info."""

    auction_code: str
    lot_code: str
    title: str | None = None
    state: str | None = None
    current_bid_eur: float | None = None
    brand: str | None = None
    title: str | None = None
    state: str | None = None
    current_bid_eur: float | None = None
    brand: str | None = None
    match_field: str  # Which field matched: 'title', 'brand', 'lot_code', 'ean'


@app.get("/search", response_model=list[SearchResultResponse])
async def search_lots(
    lot_repository: LotRepositoryDep,
    q: str = Query(..., min_length=2, description="Search query (min 2 chars)"),
    state: str | None = Query(None, description="Filter by state"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
) -> list[SearchResultResponse]:
    """Search lots by title, brand, lot code, or EAN."""
    conn = lot_repository.conn
    query_param = f"%{q}%"

    sql = """
        SELECT
            a.auction_code,
            l.lot_code,
            l.title,
            l.state,
            l.current_bid_eur,
            l.brand,
            l.ean,
            CASE
                WHEN l.lot_code LIKE ? THEN 'lot_code'
                WHEN l.ean LIKE ? THEN 'ean'
                WHEN l.brand LIKE ? THEN 'brand'
                ELSE 'title'
            END as match_field
        FROM lots l
        JOIN auctions a ON l.auction_id = a.id
        WHERE (
            l.title LIKE ? OR
            l.brand LIKE ? OR
            l.lot_code LIKE ? OR
            l.ean LIKE ?
        )
    """
    params: list = [
        query_param,
    ]

    if state:
        sql += " AND l.state = ?"
        params.append(state)

    sql += " ORDER BY l.state = 'running' DESC, l.closing_time_current ASC LIMIT ?"
    params.append(limit)

    cur = conn.execute(sql, params)
    results = []
    for row in cur.fetchall():
        results.append(
            SearchResultResponse(
                auction_code=row[0],
                lot_code=row[1],
                title=row[2],
                state=row[3],
                current_bid_eur=row[4],
                brand=row[5],
                match_field=row[7],
            )
        )
    return results


@app.get("/lots/{lot_code}", response_model=LotDetailResponse)
async def get_lot_detail(
    lot_code: str,
    lot_repository: LotRepositoryDep,
    auction_code: str | None = Query(None),
) -> LotDetailResponse:
    """Get detailed lot information including specs and reference prices."""
    lot = lot_repository.get_lot_detail(lot_code, auction_code)
    if not lot:
        raise HTTPException(status_code=404, detail=f"Lot '{lot_code}' not found")

    specs = lot_repository.get_lot_specs(lot_code, auction_code)
    ref_prices = lot_repository.get_reference_prices(lot_code, auction_code)

    return LotDetailResponse(
        auction_code=str(lot.get("auction_code", "")),
        lot_code=str(lot.get("lot_code", "")),
        title=lot.get("title"),
        url=lot.get("url"),
        state=lot.get("state"),
        current_bid_eur=lot.get("current_bid_eur"),
        bid_count=lot.get("bid_count"),
        opening_bid_eur=lot.get("opening_bid_eur"),
        closing_time_current=lot.get("closing_time_current"),
        closing_time_original=lot.get("closing_time_original"),
        brand=lot.get("brand"),
        location_city=lot.get("location_city"),
        location_country=lot.get("location_country"),
        notes=lot.get("notes"),
        specs=[
            LotSpecResponse(
                id=int(s.get("id", 0)),
                parent_id=s.get("parent_id"),
                template_id=s.get("template_id"),
                key=str(s.get("key", "")),
                value=s.get("value"),
                ean=s.get("ean"),
                price_eur=s.get("price_eur"),
                release_date=s.get("release_date"),
                category=s.get("category"),
            )
            for s in specs
        ],
        reference_prices=[
            ReferencePriceResponse(
                id=int(r.get("id", 0)),
                condition=str(r.get("condition", "used")),
                price_eur=float(r.get("price_eur", 0)),
                source=r.get("source"),
                url=r.get("url"),
                notes=r.get("notes"),
                created_at=r.get("created_at"),
            )
            for r in ref_prices
        ],
    )


@app.patch("/lots/{lot_code}", response_model=LotDetailResponse)
async def update_lot(
    lot_code: str,
    payload: LotUpdateRequest,
    lot_repository: LotRepositoryDep,
    auction_code: str | None = Query(None),
) -> LotDetailResponse:
    """Update lot notes and EAN."""
    success = lot_repository.update_lot(
        lot_code,
        auction_code,
        notes=payload.notes,
        ean=payload.ean,
    )
    if not success:
        raise HTTPException(status_code=404, detail=f"Lot '{lot_code}' not found")

    return await get_lot_detail(lot_code, lot_repository, auction_code)


@app.delete("/lots/{lot_code}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lot(
    lot_code: str,
    lot_repository: LotRepositoryDep,
    auction_code: str = Query(
        ..., description="Auction code is required to identify the lot"
    ),
) -> None:
    """Delete a lot and all related data (specs, bids, reference prices, positions)."""
    success = lot_repository.delete_lot(lot_code, auction_code)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Lot '{lot_code}' in auction '{auction_code}' not found",
        )


# =============================================================================
# Reference Prices Endpoints
# =============================================================================


@app.get(
    "/lots/{lot_code}/reference-prices", response_model=list[ReferencePriceResponse]
)
async def list_reference_prices(
    lot_code: str,
    lot_repository: LotRepositoryDep,
    auction_code: str | None = Query(None),
) -> list[ReferencePriceResponse]:
    """Get all reference prices for a lot."""
    prices = lot_repository.get_reference_prices(lot_code, auction_code)
    return [
        ReferencePriceResponse(
            id=int(r.get("id", 0)),
            condition=str(r.get("condition", "used")),
            price_eur=float(r.get("price_eur", 0)),
            source=r.get("source"),
            url=r.get("url"),
            notes=r.get("notes"),
            created_at=r.get("created_at"),
        )
        for r in prices
    ]


@app.post(
    "/lots/{lot_code}/reference-prices",
    status_code=status.HTTP_201_CREATED,
    response_model=ReferencePriceResponse,
)
async def create_reference_price(
    lot_code: str,
    payload: ReferencePriceCreateRequest,
    lot_repository: LotRepositoryDep,
    auction_code: str | None = Query(None),
) -> ReferencePriceResponse:
    """Add a reference price for a lot."""
    try:
        ref_id = lot_repository.add_reference_price(
            lot_code,
            price_eur=payload.price_eur,
            condition=payload.condition,
            source=payload.source,
            url=payload.url,
            notes=payload.notes,
            auction_code=auction_code,
        )
        return ReferencePriceResponse(
            id=ref_id,
            condition=payload.condition,
            price_eur=payload.price_eur,
            source=payload.source,
            url=payload.url,
            notes=payload.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.patch(
    "/lots/{lot_code}/reference-prices/{ref_id}", response_model=ReferencePriceResponse
)
async def update_reference_price(
    lot_code: str,
    ref_id: int,
    payload: ReferencePriceUpdateRequest,
    lot_repository: LotRepositoryDep,
) -> ReferencePriceResponse:
    """Update a reference price."""
    success = lot_repository.update_reference_price(
        ref_id,
        price_eur=payload.price_eur,
        condition=payload.condition,
        source=payload.source,
        url=payload.url,
        notes=payload.notes,
    )
    if not success:
        raise HTTPException(
            status_code=404, detail=f"Reference price {ref_id} not found"
        )

    # Get updated price
    prices = lot_repository.get_reference_prices(lot_code)
    for p in prices:
        if p.get("id") == ref_id:
            return ReferencePriceResponse(
                id=ref_id,
                condition=str(p.get("condition", "used")),
                price_eur=float(p.get("price_eur", 0)),
                source=p.get("source"),
                url=p.get("url"),
                notes=p.get("notes"),
                created_at=p.get("created_at"),
            )
    raise HTTPException(status_code=404, detail=f"Reference price {ref_id} not found")


@app.delete(
    "/lots/{lot_code}/reference-prices/{ref_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_reference_price(
    lot_code: str,
    ref_id: int,
    lot_repository: LotRepositoryDep,
) -> None:
    """Delete a reference price."""
    if not lot_repository.delete_reference_price(ref_id):
        raise HTTPException(
            status_code=404, detail=f"Reference price {ref_id} not found"
        )


# =============================================================================
# Bid History Endpoints
# =============================================================================


class BidHistoryEntryResponse(BaseModel):
    """A single bid in the lot's bid history."""

    id: int
    bidder_label: str
    amount_eur: float
    timestamp: str | None = None
    created_at: str | None = None


@app.get("/lots/{lot_code}/bid-history", response_model=list[BidHistoryEntryResponse])
async def get_lot_bid_history(
    lot_code: str,
    lot_repository: LotRepositoryDep,
    auction_code: str | None = Query(None),
) -> list[BidHistoryEntryResponse]:
    """Get bid history for a lot, ordered by most recent first."""
    history = lot_repository.get_bid_history(lot_code, auction_code)
    return [
        BidHistoryEntryResponse(
            id=h.get("id", 0),
            bidder_label=h.get("bidder_label", ""),
            amount_eur=float(h.get("amount_eur", 0)),
            timestamp=h.get("timestamp"),
            created_at=h.get("created_at"),
        )
        for h in history
    ]


class LotSpecCreateRequest(BaseModel):
    """Request to add or update a lot specification."""

    key: str
    value: str = ""
    parent_id: int | None = None
    ean: str | None = None
    price_eur: float | None = None
    template_id: int | None = None
    release_date: str | None = None
    category: str | None = None
    parent_id: int | None = None
    ean: str | None = None
    price_eur: float | None = None
    template_id: int | None = None
    release_date: str | None = None
    category: str | None = None


@app.post(
    "/lots/{lot_code}/specs",
    status_code=status.HTTP_201_CREATED,
    response_model=LotSpecResponse,
)
async def create_lot_spec(
    lot_code: str,
    payload: LotSpecCreateRequest,
    lot_repository: LotRepositoryDep,
    auction_code: str | None = Query(None),
) -> LotSpecResponse:
    """Add or update a specification for a lot."""
    try:
        spec_id = lot_repository.upsert_lot_spec(
            lot_code,
            payload.key,
            payload.value,
            auction_code,
            payload.parent_id,
            payload.ean,
            payload.price_eur,
            payload.template_id,
            payload.release_date,
            payload.category,
        )
        return LotSpecResponse(
            id=spec_id,
            parent_id=payload.parent_id,
            template_id=payload.template_id,
            key=payload.key,
            value=payload.value,
            ean=payload.ean,
            price_eur=payload.price_eur,
            release_date=payload.release_date,
            category=payload.category,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.delete("/lots/{lot_code}/specs/{spec_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lot_spec(
    lot_code: str,
    spec_id: int,
    lot_repository: LotRepositoryDep,
) -> None:
    """Delete a lot specification."""
    if not lot_repository.delete_lot_spec(spec_id):
        raise HTTPException(status_code=404, detail=f"Spec {spec_id} not found")


# =============================================================================
# Spec Templates Endpoints - Reusable specifications across lots
# =============================================================================


class SpecTemplateResponse(BaseModel):
    """A reusable specification template."""

    id: int
    parent_id: int | None = None
    title: str
    value: str | None = None
    ean: str | None = None
    price_eur: float | None = None
    release_date: str | None = None
    category: str | None = None
    created_at: str | None = None
    value: str | None = None
    ean: str | None = None
    price_eur: float | None = None
    release_date: str | None = None
    category: str | None = None
    created_at: str | None = None


class SpecTemplateCreateRequest(BaseModel):
    """Request to create a spec template."""

    title: str
    value: str | None = None
    ean: str | None = None
    price_eur: float | None = None
    parent_id: int | None = None
    release_date: str | None = None
    category: str | None = None
    value: str | None = None
    ean: str | None = None
    price_eur: float | None = None
    parent_id: int | None = None
    release_date: str | None = None
    category: str | None = None


class SpecTemplateUpdateRequest(BaseModel):
    """Request to update a spec template."""
    title: str | None = None
    value: str | None = None
    ean: str | None = None
    price_eur: float | None = None
    release_date: str | None = None
    category: str | None = None


class ApplyTemplateRequest(BaseModel):
    """Request to apply a template to a lot."""

    template_id: int
    parent_id: int | None = None


@app.get("/spec-templates", response_model=list[SpecTemplateResponse])
async def list_spec_templates(
    lot_repository: LotRepositoryDep,
    parent_id: int | None = Query(None),
) -> list[SpecTemplateResponse]:
    """List all spec templates, optionally filtered by parent."""
    templates = lot_repository.list_spec_templates(parent_id)
    return [SpecTemplateResponse(**t) for t in templates]


@app.post(
    "/spec-templates",
    status_code=status.HTTP_201_CREATED,
    response_model=SpecTemplateResponse,
)
async def create_spec_template(
    payload: SpecTemplateCreateRequest,
    lot_repository: LotRepositoryDep,
) -> SpecTemplateResponse:
    """Create a new spec template."""
    template_id = lot_repository.create_spec_template(
        title=payload.title,
        value=payload.value,
        ean=payload.ean,
        price_eur=payload.price_eur,
        parent_id=payload.parent_id,
        release_date=payload.release_date,
        category=payload.category,
    )
    return SpecTemplateResponse(
        id=template_id,
        parent_id=payload.parent_id,
        title=payload.title,
        value=payload.value,
        ean=payload.ean,
        price_eur=payload.price_eur,
        release_date=payload.release_date,
        category=payload.category,
    )


@app.patch("/spec-templates/{template_id}", response_model=SpecTemplateResponse)
async def update_spec_template(
    template_id: int,
    payload: SpecTemplateUpdateRequest,
    lot_repository: LotRepositoryDep,
) -> SpecTemplateResponse:
    """Update a spec template."""
    if not lot_repository.update_spec_template(
        template_id,
        title=payload.title,
        value=payload.value,
        ean=payload.ean,
        price_eur=payload.price_eur,
        release_date=payload.release_date,
        category=payload.category,
    ):
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")

    template = lot_repository.get_spec_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
    return SpecTemplateResponse(**template)


@app.delete("/spec-templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_spec_template(
    template_id: int,
    lot_repository: LotRepositoryDep,
) -> None:
    """Delete a spec template."""
    if not lot_repository.delete_spec_template(template_id):
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")


@app.post(
    "/lots/{lot_code}/apply-template",
    status_code=status.HTTP_201_CREATED,
    response_model=LotSpecResponse,
)
async def apply_template_to_lot(
    lot_code: str,
    payload: ApplyTemplateRequest,
    lot_repository: LotRepositoryDep,
    auction_code: str | None = Query(None),
) -> LotSpecResponse:
    """Apply a spec template to a lot."""
    try:
        template = lot_repository.get_spec_template(payload.template_id)
        if not template:
            raise HTTPException(
                status_code=404, detail=f"Template {payload.template_id} not found"
            )

        spec_id = lot_repository.apply_template_to_lot(
            lot_code=lot_code,
            template_id=payload.template_id,
            auction_code=auction_code,
            parent_id=payload.parent_id,
        )
        return LotSpecResponse(
            id=spec_id,
            parent_id=payload.parent_id,
            template_id=payload.template_id,
            key=template["title"],
            value=template.get("value"),
            ean=template.get("ean"),
            price_eur=template.get("price_eur"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/positions/batch", response_model=PositionBatchResponse)
async def upsert_positions(
    payload: PositionBatchRequest,
    repository: PositionRepositoryDep,
) -> PositionBatchResponse:
    try:
        updates = [
            PositionUpdateData(
                buyer_label=update.buyer_label,
                lot_code=update.lot_code,
                auction_code=update.auction_code,
                max_budget_total_eur=update.max_budget_total_eur,
                preferred_bid_eur=update.preferred_bid_eur,
                watch=update.watch,
            )
            for update in payload.updates
        ]
        result = await position_service.upsert_positions(
            repository=repository, updates=updates, event_publisher=event_bus.publish
        )
        return PositionBatchResponse(
            updated=cast(int, result.get("updated", 0)),
            created=cast(int, result.get("created", 0)),
            errors=cast(list[str], result.get("errors", [])),
        )
    except ValueError as exc:  # raised when buyer or lot not found
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@app.get("/positions", response_model=list[PositionResponse])
async def list_positions(
    repository: PositionRepositoryDep,
    buyer: str | None = Query(None, description="Filter by buyer label"),
) -> list[PositionResponse]:
    """List all tracked positions, optionally filtered by buyer."""
    from troostwatch.services.positions import PositionsService

    rows = repository.list(buyer_label=buyer)
    positions = [PositionsService._row_to_dto(row) for row in rows]
    return [
        PositionResponse(
            buyer_label=pos.buyer_label,
            lot_code=pos.lot_code,
            auction_code=pos.auction_code,
            track_active=pos.track_active,
            max_budget_total_eur=pos.max_budget_total_eur,
            my_highest_bid_eur=pos.my_highest_bid_eur,
            lot_title=pos.lot_title,
            lot_state=pos.lot_state,
            current_bid_eur=pos.current_bid_eur,
        )
        for pos in positions
    ]


@app.delete(
    "/positions/{buyer_label}/{lot_code}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_position(
    buyer_label: str,
    lot_code: str,
    repository: PositionRepositoryDep,
    auction_code: str | None = Query(None),
) -> None:
    """Delete a tracked position."""
    repository.delete(
        buyer_label=buyer_label,
        lot_code=lot_code,
        auction_code=auction_code,
    )


@app.get("/buyers", response_model=list[BuyerResponse])
async def list_buyers(
    service: BuyerServiceDep,
) -> list[BuyerResponse]:
    buyers = service.list_buyers()
    result: list[BuyerResponse] = []
    for buyer in buyers:
        result.append(
            BuyerResponse(
                id=buyer.id,
                label=buyer.label,
                name=buyer.name,
                notes=buyer.notes,
            )
        )
    return result


@app.post(
    "/buyers", response_model=BuyerCreateResponse, status_code=status.HTTP_201_CREATED
)
async def create_buyer(
    payload: BuyerCreateRequest,
    service: BuyerServiceDep,
) -> BuyerCreateResponse:
    try:
        result: BuyerCreateDTO = await service.create_buyer(
            label=payload.label,
            name=payload.name,
            notes=payload.notes,
        )
        return BuyerCreateResponse(status="created", label=result.label)
    except BuyerAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.delete("/buyers/{label}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_buyer(label: str, service: BuyerServiceDep) -> None:
    await service.delete_buyer(label=label)


# =============================================================================
# Bids Endpoints
# =============================================================================


def _bid_row_to_response(bid: dict[str, Any]) -> BidResponse:
    """Convert a bid repository row to a BidResponse."""
    return BidResponse(
        id=cast(int, bid.get("id", 0)),
        buyer_label=str(bid.get("buyer_label", "")),
        lot_code=str(bid.get("lot_code", "")),
        auction_code=str(bid.get("auction_code", "")),
        lot_title=str(bid["lot_title"]) if bid.get("lot_title") else None,
        amount_eur=cast(float, bid.get("amount_eur", 0.0)),
        placed_at=str(bid.get("placed_at", "")),
        note=str(bid["note"]) if bid.get("note") else None,
    )


@app.get("/bids", response_model=list[BidResponse])
async def list_bids(
    repo: BidRepositoryDep,
    buyer: str | None = Query(None, description="Filter by buyer label"),
    lot_code: str | None = Query(None, description="Filter by lot code"),
    limit: int = Query(100, ge=1, le=500),
) -> list[BidResponse]:
    """List recorded bids with optional filters."""
    bids = repo.list(buyer_label=buyer, lot_code=lot_code, limit=limit)
    return [_bid_row_to_response(bid) for bid in bids]


@app.post("/bids", status_code=status.HTTP_201_CREATED, response_model=BidResponse)
async def create_bid(
    payload: BidCreateRequest,
    repo: BidRepositoryDep,
) -> BidResponse:
    """Record a new bid (local only, does not submit to Troostwijk)."""
    try:
        repo.record_bid(
            buyer_label=payload.buyer_label,
            auction_code=payload.auction_code,
            lot_code=payload.lot_code,
            amount_eur=payload.amount_eur,
            note=payload.note,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    # Fetch the created bid to return it
    bids = repo.list(
        buyer_label=payload.buyer_label, lot_code=payload.lot_code, limit=1
    )
    if not bids:
        raise HTTPException(status_code=500, detail="Bid created but not found")

    return _bid_row_to_response(bids[0])


# =============================================================================
# Report Endpoints
# =============================================================================


def get_reporting_service() -> ReportingService:
    """Dependency that provides a ReportingService."""
    return ReportingService.from_sqlite_path("troostwatch.db")


ReportingServiceDep = Annotated[ReportingService, Depends(get_reporting_service)]


@app.get("/reports/buyer/{buyer_label}", response_model=BuyerSummaryResponse)
async def get_buyer_report(
    buyer_label: str,
    service: ReportingServiceDep,
) -> BuyerSummaryResponse:
    """Get exposure and position summary for a buyer."""
    summary = service.get_buyer_summary(buyer_label)
    summary_dict = summary.to_dict()
    return BuyerSummaryResponse(
        buyer_label=buyer_label,
        tracked_count=summary_dict["tracked_count"],
        open_count=summary_dict["open_count"],
        closed_count=summary_dict["closed_count"],
        open_exposure_min_eur=summary_dict["open_exposure_min_eur"],
        open_exposure_max_eur=summary_dict["open_exposure_max_eur"],
        open_tracked_lots=[
            TrackedLotSummaryResponse(**lot)
            for lot in summary_dict["open_tracked_lots"]
        ],
        won_lots=[TrackedLotSummaryResponse(**lot) for lot in summary_dict["won_lots"]],
    )


# =============================================================================
# Auction Endpoints
# =============================================================================


# Use get_auction_repository from dependencies module


# =============================================================================
# Dashboard Stats Endpoint
# =============================================================================


class DashboardStatsResponse(BaseModel):
    """Dashboard statistics overview."""

    total_auctions: int
    active_auctions: int
    total_lots: int
    running_lots: int
    scheduled_lots: int
    closed_lots: int
    total_bids: int
    total_positions: int
    total_buyers: int


@app.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    lot_repository: LotRepositoryDep,
    buyer_repository: BuyerRepositoryDep,
    position_repository: PositionRepositoryDep,
) -> DashboardStatsResponse:
    """Get dashboard statistics overview."""
    conn = lot_repository.conn

    # Auction counts
    auction_total = conn.execute("SELECT COUNT(*) FROM auctions").fetchone()[0]
    auction_active = conn.execute(
        """SELECT COUNT(DISTINCT a.id) FROM auctions a
           JOIN lots l ON l.auction_id = a.id
           WHERE l.state IN ('running', 'scheduled')"""
    ).fetchone()[0]

    # Lot counts by state
    lot_total = conn.execute("SELECT COUNT(*) FROM lots").fetchone()[0]
    lot_running = conn.execute(
        "SELECT COUNT(*) FROM lots WHERE state = 'running'"
    ).fetchone()[0]
    lot_scheduled = conn.execute(
        "SELECT COUNT(*) FROM lots WHERE state = 'scheduled'"
    ).fetchone()[0]
    lot_closed = conn.execute(
        "SELECT COUNT(*) FROM lots WHERE state = 'closed'"
    ).fetchone()[0]

    # Other counts
    bid_total = conn.execute("SELECT COUNT(*) FROM my_bids").fetchone()[0]
    position_total = conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0]
    buyer_total = conn.execute("SELECT COUNT(*) FROM buyers").fetchone()[0]

    return DashboardStatsResponse(
        total_auctions=auction_total,
        active_auctions=auction_active,
        total_lots=lot_total,
        running_lots=lot_running,
        scheduled_lots=lot_scheduled,
        closed_lots=lot_closed,
        total_bids=bid_total,
        total_positions=position_total,
        total_buyers=buyer_total,
    )


@app.get("/auctions", response_model=list[AuctionResponse])
async def list_auctions(
    repo: AuctionRepositoryDep,
    include_inactive: bool = Query(
        False, description="Include auctions without active lots"
    ),
) -> list[AuctionResponse]:
    """List all auctions, optionally including those without active lots."""
    auctions = repo.list(only_active=not include_inactive)
    return [
        AuctionResponse(
            auction_code=str(a.get("auction_code", "")),
            title=a.get("title"),
            url=a.get("url"),
            starts_at=a.get("starts_at"),
            ends_at_planned=a.get("ends_at_planned"),
            active_lots=int(a.get("active_lots") or 0),
            lot_count=int(a.get("lot_count") or 0),
        )
        for a in auctions
    ]


class AuctionDetailResponse(BaseModel):
    """Detailed auction information."""

    auction_code: str
    title: str | None = None
    url: str | None = None
    starts_at: str | None = None
    ends_at_planned: str | None = None
    title: str | None = None
    url: str | None = None
    starts_at: str | None = None
    ends_at_planned: str | None = None
    lot_count: int = 0


class AuctionUpdateRequest(BaseModel):
    """Request to update an auction."""
    title: str | None = None
    url: str | None = None
    starts_at: str | None = None
    ends_at_planned: str | None = None

    title: str | None = None
    url: str | None = None
    starts_at: str | None = None
    ends_at_planned: str | None = None


class AuctionDeleteResponse(BaseModel):
    """Response after deleting an auction."""

    status: str
    auction_deleted: int
    lots_deleted: int


@app.get("/auctions/{auction_code}", response_model=AuctionDetailResponse)
async def get_auction(
    auction_code: str,
    repo: AuctionRepositoryDep,
) -> AuctionDetailResponse:
    """Get a single auction by code."""
    auction = repo.get_by_code(auction_code)
    if not auction:
        raise HTTPException(
            status_code=404, detail=f"Auction '{auction_code}' not found"
        )
    return AuctionDetailResponse(
        auction_code=auction["auction_code"],
        title=auction.get("title"),
        url=auction.get("url"),
        starts_at=auction.get("starts_at"),
        ends_at_planned=auction.get("ends_at_planned"),
        lot_count=auction.get("lot_count", 0),
    )


@app.patch("/auctions/{auction_code}", response_model=AuctionDetailResponse)
async def update_auction(
    auction_code: str,
    payload: AuctionUpdateRequest,
    repo: AuctionRepositoryDep,
) -> AuctionDetailResponse:
    """Update an auction."""
    if not repo.update(
        auction_code,
        title=payload.title,
        url=payload.url,
        starts_at=payload.starts_at,
        ends_at_planned=payload.ends_at_planned,
    ):
        raise HTTPException(
            status_code=404, detail=f"Auction '{auction_code}' not found"
        )

    updated = repo.get_by_code(auction_code)
    if not updated:
        raise HTTPException(
            status_code=404, detail=f"Auction '{auction_code}' not found after update"
        )

    return AuctionDetailResponse(
        auction_code=updated["auction_code"],
        title=updated.get("title"),
        url=updated.get("url"),
        starts_at=updated.get("starts_at"),
        ends_at_planned=updated.get("ends_at_planned"),
        lot_count=updated.get("lot_count", 0),
    )


@app.delete("/auctions/{auction_code}", response_model=AuctionDeleteResponse)
async def delete_auction(
    auction_code: str,
    repo: AuctionRepositoryDep,
    delete_lots: bool = Query(
        False, description="Also delete all lots in this auction"
    ),
) -> AuctionDeleteResponse:
    """Delete an auction. Optionally delete all associated lots."""
    result = repo.delete(auction_code, delete_lots=delete_lots)
    if result["auction"] == 0:
        raise HTTPException(
            status_code=404, detail=f"Auction '{auction_code}' not found"
        )
    return AuctionDeleteResponse(
        status="deleted",
        auction_deleted=result["auction"],
        lots_deleted=result["lots"],
    )


# =============================================================================
# Lot Management Endpoints
# =============================================================================


def get_lot_management_service(
    lot_repo: LotRepositoryDep,
    auction_repo: AuctionRepositoryDep,
) -> LotManagementService:
    """Dependency that provides a LotManagementService."""
    return LotManagementService(
        lot_repository=lot_repo,
        auction_repository=auction_repo,
    )


LotManagementServiceDep = Annotated[
    LotManagementService, Depends(get_lot_management_service)
]


@app.post(
    "/lots", status_code=status.HTTP_201_CREATED, response_model=LotCreateResponse
)
async def create_lot(
    payload: LotCreateRequest,
    service: LotManagementServiceDep,
) -> LotCreateResponse:
    """Manually add or update a lot in the database."""
    from datetime import datetime, timezone

    seen_at = datetime.now(timezone.utc).isoformat()

    lot_input = LotInput(
        auction_code=payload.auction_code,
        lot_code=payload.lot_code,
        title=payload.title,
        url=payload.url,
        state=payload.state,
        opens_at=payload.opens_at,
        closing_time=payload.closing_time,
        bid_count=payload.bid_count,
        opening_bid_eur=payload.opening_bid_eur,
        current_bid_eur=payload.current_bid_eur,
        location_city=payload.location_city,
        location_country=payload.location_country,
        auction_title=payload.auction_title,
        auction_url=payload.auction_url,
    )

    lot_code = service.add_lot(lot_input, seen_at)
    return LotCreateResponse(
        status="created",
        lot_code=lot_code,
        auction_code=payload.auction_code,
    )


@app.post(
    "/sync", status_code=status.HTTP_202_ACCEPTED, response_model=SyncSummaryResponse
)
async def trigger_sync(
    request: SyncRequest, service: SyncServiceDep
) -> SyncSummaryResponse:
    summary = await service.run_sync(
        auction_code=request.auction_code,
        auction_url=request.auction_url,
        max_pages=request.max_pages,
        dry_run=request.dry_run,
    )
    summary_dict = summary.to_dict()
    # Convert nested result if present
    result_data = summary_dict.get("result")
    result = None
    if result_data and isinstance(result_data, dict):
        result = SyncRunResultResponse(**result_data)
    return SyncSummaryResponse(
        status=str(summary_dict.get("status") or "error"),
        auction_code=(
            str(summary_dict.get("auction_code"))
            if summary_dict.get("auction_code")
            else None
        ),
        result=result,
        error=str(summary_dict.get("error")) if summary_dict.get("error") else None,
    )


@app.post(
    "/live-sync/start",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=LiveSyncControlResponse,
)
async def start_live_sync(
    request: LiveSyncStartRequest, service: SyncServiceDep
) -> LiveSyncControlResponse:
    result = await service.start_live_sync(
        auction_code=request.auction_code,
        auction_url=request.auction_url,
        max_pages=request.max_pages,
        dry_run=request.dry_run,
        interval_seconds=request.interval_seconds,
    )
    return LiveSyncControlResponse(
        state=str(result.get("state") or "unknown"),
        detail=str(result.get("detail")) if result.get("detail") else None,
    )


@app.post(
    "/live-sync/pause",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=LiveSyncControlResponse,
)
async def pause_live_sync(
    service: SyncServiceDep,
) -> LiveSyncControlResponse:
    result = await service.pause_live_sync()
    return LiveSyncControlResponse(
        state=str(result.get("state") or "unknown"),
        detail=str(result.get("detail")) if result.get("detail") else None,
    )


@app.post(
    "/live-sync/stop",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=LiveSyncControlResponse,
)
async def stop_live_sync(
    service: SyncServiceDep,
) -> LiveSyncControlResponse:
    result = await service.stop_live_sync()
    return LiveSyncControlResponse(
        state=str(result.get("state") or "unknown"),
        detail=str(result.get("detail")) if result.get("detail") else None,
    )


@app.get("/live-sync/status", response_model=LiveSyncStatusResponse)
async def get_live_sync_status(
    service: SyncServiceDep,
) -> LiveSyncStatusResponse:
    status_dict = service.get_live_sync_status()
    return LiveSyncStatusResponse(
        state=cast(str, status_dict.get("state", "idle")),
        last_sync=cast(str | None, status_dict.get("last_sync")),
        next_sync=cast(str | None, status_dict.get("next_sync")),
        current_auction=cast(str | None, status_dict.get("current_auction")),
    )


@app.websocket("/ws/lots")
async def lot_updates(websocket: WebSocket) -> None:
    await event_bus.subscribe(websocket)
    try:
        while True:
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
    finally:
        await event_bus.unsubscribe(websocket)

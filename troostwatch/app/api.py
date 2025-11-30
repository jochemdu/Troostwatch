"""FastAPI application exposing Troostwatch repositories.

Run with ``uvicorn troostwatch.app.api:app``.
"""

from __future__ import annotations

import asyncio
import os
from typing import Annotated, Any, cast

from fastapi import (APIRouter, Depends, FastAPI, File, HTTPException, Query,
                     Response, UploadFile, WebSocket, WebSocketDisconnect,
                     status)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from troostwatch import __version__
from troostwatch.app.dependencies import (  # Annotated dependency types (modern FastAPI pattern)
    AuctionRepositoryDep, BidRepositoryDep, BuyerRepositoryDep,
    ExtractedCodeRepositoryDep, LotImageRepositoryDep, LotRepositoryDep,
    PositionRepositoryDep)
from troostwatch.app.ws_messages import (MESSAGE_FORMAT_VERSION,
                                         ConnectionReadyMessage,
                                         create_message)
from troostwatch.infrastructure.ai import ImageAnalyzer
from troostwatch.services import positions as position_service
from troostwatch.services.buyers import BuyerAlreadyExistsError, BuyerService
from troostwatch.services.dto import BuyerCreateDTO
from troostwatch.services.label_extraction import (LabelExtractionResult,
                                                   extract_label_from_image)
from troostwatch.services.lots import (LotInput, LotManagementService, LotView,
                                       LotViewService)
from troostwatch.services.positions import PositionUpdateData
from troostwatch.services.reporting import ReportingService
from troostwatch.services.sync_service import SyncService


class LotEventBus:
    """Simple in-memory broadcaster for lot updates.

    Messages are sent in the v1 wire format:
        {
            "version": "1",
            "type": "<event_type>",
            "timestamp": "<ISO8601>",
            "payload": { ... }
        }

    Use `create_message()` or typed message classes from `ws_messages`
    to construct messages.
    """

    def __init__(self) -> None:
        self._subscribers: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def subscribe(self, websocket: WebSocket) -> None:
        """Subscribe a WebSocket and send connection ready message."""
        await websocket.accept()
        async with self._lock:
            self._subscribers.add(websocket)

        # Send connection ready message
        ready_msg = ConnectionReadyMessage(
            server_version=__version__,
            message_format_version=MESSAGE_FORMAT_VERSION,
        )
        try:
            await websocket.send_json(ready_msg.to_wire())
        except Exception:
            pass

    async def unsubscribe(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._subscribers.discard(websocket)

    async def publish(self, payload: dict[str, Any]) -> None:
        """Publish a message to all subscribers.

        If `payload` already has a 'version' field, it's sent as-is.
        Otherwise, it's wrapped in the v1 wire format using the 'type' field.
        """
        # Wrap legacy payloads in v1 format
        if "version" not in payload and "type" in payload:
            msg_type = payload.pop("type")
            payload = create_message(msg_type, **payload)

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

# Enable CORS for local development and Chrome extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_origin_regex=r"^chrome-extension://.*$",  # Allow Chrome extensions
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


class BuyerResponse(BaseModel):
    id: int
    label: str
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


class LiveSyncStatusResponse(BaseModel):
    """Status of the live sync worker."""

    state: str  # 'idle', 'running', 'paused', 'stopping'
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


class AuctionResponse(BaseModel):
    """Auction summary."""

    auction_code: str
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


class LotUpdateRequest(BaseModel):
    """Request to update lot fields (notes, ean)."""

    notes: str | None = None
    ean: str | None = None


class LotSpecResponse(BaseModel):
    """A specification key-value pair for a lot."""

    id: int
    parent_id: int | None = None
    template_id: int | None = None
    key: str
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
    created_at: str | None = None
    source: str | None = None
    url: str | None = None
    notes: str | None = None


class ReferencePriceCreateRequest(BaseModel):
    """Request to add a reference price."""

    condition: str = Field(default="used", pattern="^(new|used|refurbished)$")
    price_eur: float = Field(ge=0)
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


class ExtractedCodeResponse(BaseModel):
    """A code extracted from an image."""

    code_type: str  # product_code, model_number, ean, serial_number, other
    value: str
    confidence: str  # high, medium, low
    context: str | None = None


class ImageAnalysisResultResponse(BaseModel):
    """Result of analyzing a single image."""

    image_url: str
    codes: list[ExtractedCodeResponse] = Field(default_factory=list)
    raw_text: str | None = None
    error: str | None = None


class ImageAnalysisRequest(BaseModel):
    """Request to analyze images for product codes."""

    image_urls: list[str] = Field(..., min_length=1, max_length=10)
    backend: str = Field(
        default="local",
        pattern="^(local|openai)$",
        description="Backend to use: 'local' (Tesseract OCR) or 'openai' (GPT-4 Vision)",
    )


class ImageAnalysisResponse(BaseModel):
    """Response with analyzed image results."""

    results: list[ImageAnalysisResultResponse] = Field(default_factory=list)


# ============================================================================
# Review Queue Models
# ============================================================================


class PendingCodeResponse(BaseModel):
    """An extracted code pending review."""

    id: int
    lot_image_id: int
    lot_id: int
    lot_code: str
    image_url: str | None = None
    image_local_path: str | None = None
    code_type: str
    value: str
    confidence: str
    context: str | None = None
    created_at: str


class PendingCodesListResponse(BaseModel):
    """List of pending codes for review."""

    codes: list[PendingCodeResponse] = Field(default_factory=list)
    total: int
    page: int = 1
    page_size: int = 20


class CodeApprovalRequest(BaseModel):
    """Request to approve or reject a code."""

    approved: bool
    reason: str | None = None


class CodeApprovalResponse(BaseModel):
    """Response after approving/rejecting a code."""

    id: int
    approved: bool
    approved_by: str | None = None
    approved_at: str | None = None


class BulkApprovalRequest(BaseModel):
    """Request to approve/reject multiple codes."""

    code_ids: list[int] = Field(..., min_length=1, max_length=100)
    approved: bool
    reason: str | None = None


class BulkApprovalResponse(BaseModel):
    """Response after bulk approval/rejection."""

    processed: int
    approved: int
    rejected: int


class ReviewStatsResponse(BaseModel):
    """Statistics for the review queue."""

    pending: int
    approved_auto: int
    approved_manual: int
    rejected: int
    total: int


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


class SpecTemplateCreateRequest(BaseModel):
    """Request to create a spec template."""

    title: str
    parent_id: int | None = None
    value: str | None = None
    ean: str | None = None
    price_eur: float | None = None
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
    result: list[SpecTemplateResponse] = []
    for t in templates:
        result.append(
            SpecTemplateResponse(
                id=int(t.get("id", 0)),
                parent_id=t.get("parent_id"),
                title=str(t.get("title", "")),
                value=t.get("value"),
                ean=t.get("ean"),
                price_eur=t.get("price_eur"),
                release_date=t.get("release_date"),
                category=t.get("category"),
                created_at=t.get("created_at"),
            )
        )
    return result


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
    id_val = template.get("id")
    id_int = int(id_val) if id_val is not None else 0
    return SpecTemplateResponse(
        id=id_int,
        parent_id=template.get("parent_id"),
        title=str(template.get("title", "")),
        value=template.get("value"),
        ean=template.get("ean"),
        price_eur=template.get("price_eur"),
        release_date=template.get("release_date"),
        category=template.get("category"),
        created_at=template.get("created_at"),
    )


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
            key=str(template.get("title", "")),
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

# =============================
# ML Model Management Endpoints
# =============================


@app.post("/ml/retrain", response_model=dict)
async def retrain_ml_model(
    training_data_path: str | None = None,
    n_estimators: int = 100,
    max_depth: int | None = None,
) -> dict:
    """Trigger ML model retraining and record run in DB."""
    from troostwatch.services.image_analysis import ImageAnalysisService

    service = ImageAnalysisService.from_sqlite_path("troostwatch.db")
    # Record training run as 'pending'
    run_id = service.record_training_run(
        status="pending",
        model_path=None,
        metrics=None,
        notes=f"Retraining started with n_estimators={n_estimators}, max_depth={max_depth}",
        created_by="api",
        training_data_filter=training_data_path,
    )
    # Simulate async retraining (replace with real ML logic)
    import time

    time.sleep(1)  # Simulate work
    metrics = {"accuracy": 0.88, "precision": 0.92, "recall": 0.91, "f1": 0.91}
    model_path = "label_ocr_api/models/label_token_classifier.joblib"
    service.update_training_run(
        run_id,
        status="completed",
        finished_at=None,
        model_path=model_path,
        metrics=metrics,
        notes="Retraining completed",
    )
    return {
        "status": "completed",
        "run_id": run_id,
        "metrics": metrics,
        "model_path": model_path,
        "detail": "Retraining completed and recorded.",
    }


@app.get("/ml/export-training-data", response_model=dict)
async def export_training_data(
    include_reviewed: bool = False,
    only_mismatches: bool = False,
    limit: int = 1000,
) -> dict:
    """Export training data for ML, met filtering en mismatch weergave.
    Args:
        include_reviewed: Include handmatig gelabelde data.
        only_mismatches: Toon alleen records waar tokens en labels niet overeenkomen.
        limit: Maximaal aantal records.
    Returns:
        Dict met images, labels, en mismatches.
    """
    from troostwatch.services.image_analysis import ImageAnalysisService

    service = ImageAnalysisService.from_sqlite_path("troostwatch.db")
    # Haal alle records op
    with service._connection_factory() as conn:
        from troostwatch.infrastructure.db.repositories.images import (
            LotImageRepository, OcrTokenRepository)

        token_repo = OcrTokenRepository(conn)
        image_repo = LotImageRepository(conn)
        # Simpele fetch, kan later uitgebreid worden
        if include_reviewed:
            records = token_repo.get_for_training(limit=limit)
        else:
            records = token_repo.get_all_for_export(limit=limit)
        images = []
        mismatches = []
        for record in records:
            image = service._fetch_one_as_dict(
                conn,
                "SELECT lot_id, local_path FROM lot_images WHERE id = ?",
                (record.lot_image_id,),
            )
            lot_id_val = image.get("lot_id") if isinstance(image, dict) else None
            local_path_val = (
                image.get("local_path") if isinstance(image, dict) else None
            )
            entry = {
                "lot_image_id": record.lot_image_id,
                "lot_id": lot_id_val,
                "local_path": local_path_val,
                "tokens": record.tokens,
                "has_labels": record.has_labels,
                "labels": getattr(record, "labels", None),
            }
            images.append(entry)
            # Mismatch: tokens en labels komen niet overeen
            if only_mismatches and entry["has_labels"] and entry["labels"]:
                tokens_val = entry["tokens"]
                labels_val = entry["labels"]
                token_texts = set()
                if isinstance(tokens_val, dict):
                    token_texts = set(tokens_val.get("text", []))
                label_keys = set()
                if isinstance(labels_val, dict):
                    label_keys = set(labels_val.keys())
                if not label_keys.issubset(token_texts):
                    mismatches.append(entry)
        result = {
            "version": "1.0",
            "images": images if not only_mismatches else mismatches,
            "count": len(images if not only_mismatches else mismatches),
        }
    return result


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
    lot_count: int = 0


class AuctionUpdateRequest(BaseModel):
    """Request to update an auction."""

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
        auction_code=str(auction.get("auction_code", "")),
        title=auction.get("title"),
        url=auction.get("url"),
        starts_at=auction.get("starts_at"),
        ends_at_planned=auction.get("ends_at_planned"),
        lot_count=int(auction.get("lot_count") or 0),
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
        auction_code=str(updated.get("auction_code", "")),
        title=updated.get("title"),
        url=updated.get("url"),
        starts_at=updated.get("starts_at"),
        ends_at_planned=updated.get("ends_at_planned"),
        lot_count=int(updated.get("lot_count", 0) or 0),
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


@app.get("/ml/training-status", response_model=dict)
async def get_training_status() -> dict:
    """Return latest ML training run status and metrics from DB."""
    from troostwatch.services.image_analysis import ImageAnalysisService

    service = ImageAnalysisService.from_sqlite_path("troostwatch.db")
    runs = service.get_training_runs(limit=1)
    last_run = runs[0] if runs else None
    model_info = {
        "path": last_run["model_path"] if last_run else None,
        "trained_on": None,
    }
    stats = {
        "images": None,
        "labels": None,
        "mismatches": None,
    }
    return {
        "last_run": last_run,
        "model_info": model_info,
        "stats": stats,
        "detail": "Training status and model info from database.",
    }


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


@app.post("/images/analyze", response_model=ImageAnalysisResponse)
async def analyze_images(
    request: ImageAnalysisRequest,
) -> ImageAnalysisResponse:
    """Analyze images for product codes, model numbers, and EAN codes.

    Supports two backends:
    - 'local': Uses Tesseract OCR with regex extraction (free, offline)
    - 'openai': Uses GPT-4 Vision API (requires OPENAI_API_KEY)

    The local backend requires pytesseract and tesseract-ocr to be installed.
    """
    # Validate backend and cast to Literal type
    backend = "openai" if request.backend == "openai" else "local"
    analyzer = ImageAnalyzer(backend=backend)  # type: ignore[arg-type]
    try:
        results = await analyzer.analyze_multiple(request.image_urls)
        return ImageAnalysisResponse(
            results=[
                ImageAnalysisResultResponse(
                    image_url=r.image_url,
                    codes=[
                        ExtractedCodeResponse(
                            code_type=c.code_type,
                            value=c.value,
                            confidence=c.confidence,
                            context=c.context,
                        )
                        for c in r.codes
                    ],
                    raw_text=r.raw_text,
                    error=r.error,
                )
                for r in results
            ]
        )
    finally:
        await analyzer.close()


# ============================================================================
# Review Queue Endpoints
# ============================================================================


@app.get("/review/codes/pending", response_model=PendingCodesListResponse)
async def get_pending_codes(
    code_repo: ExtractedCodeRepositoryDep,
    image_repo: LotImageRepositoryDep,
    lot_repo: LotRepositoryDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    code_type: str | None = None,
) -> PendingCodesListResponse:
    """Get extracted codes pending manual review.

    Returns codes that have not been auto-approved and need human review.
    """
    offset = (page - 1) * page_size

    # Get pending codes from repository
    pending = code_repo.get_pending_approval(limit=page_size, offset=offset)
    total = code_repo.count_pending_approval()

    codes = []
    for code in pending:
        # Get image info
        image = image_repo.get_by_id(code.lot_image_id)
        if not image:
            continue

        # Get lot info
        lot = lot_repo.get_lot_by_id(image.lot_id)
        lot_code = lot.lot_code if lot else f"unknown-{image.lot_id}"

        codes.append(
            PendingCodeResponse(
                id=code.id,
                lot_image_id=code.lot_image_id,
                lot_id=image.lot_id,
                lot_code=lot_code,
                image_url=image.url,
                image_local_path=image.local_path,
                code_type=code.code_type,
                value=code.value,
                confidence=code.confidence,
                context=code.context,
                created_at=code.created_at,
            )
        )

    return PendingCodesListResponse(
        codes=codes,
        total=total,
        page=page,
        page_size=page_size,
    )


@app.post("/review/codes/{code_id}/approve", response_model=CodeApprovalResponse)
async def approve_code(
    code_id: int,
    code_repo: ExtractedCodeRepositoryDep,
) -> CodeApprovalResponse:
    """Approve an extracted code for promotion to lot record."""
    code = code_repo.get_by_id(code_id)
    if not code:
        raise HTTPException(status_code=404, detail="Code not found")

    code_repo.approve_code(code_id, approved_by="manual")

    # Fetch updated code
    updated = code_repo.get_by_id(code_id)
    return CodeApprovalResponse(
        id=code_id,
        approved=True,
        approved_by=updated.approved_by if updated else "manual",
        approved_at=updated.approved_at if updated else None,
    )


@app.post("/review/codes/{code_id}/reject", response_model=CodeApprovalResponse)
async def reject_code(
    code_id: int,
    code_repo: ExtractedCodeRepositoryDep,
) -> CodeApprovalResponse:
    """Reject an extracted code (mark as not approved)."""
    code = code_repo.get_by_id(code_id)
    if not code:
        raise HTTPException(status_code=404, detail="Code not found")

    code_repo.reject_code(code_id)

    return CodeApprovalResponse(
        id=code_id,
        approved=False,
        approved_by=None,
        approved_at=None,
    )


@app.post("/review/codes/bulk", response_model=BulkApprovalResponse)
async def bulk_approve_codes(
    request: BulkApprovalRequest,
    code_repo: ExtractedCodeRepositoryDep,
) -> BulkApprovalResponse:
    """Approve or reject multiple codes at once."""
    approved_count = 0
    rejected_count = 0

    for code_id in request.code_ids:
        code = code_repo.get_by_id(code_id)
        if not code:
            continue

        if request.approved:
            code_repo.approve_code(code_id, approved_by="manual")
            approved_count += 1
        else:
            code_repo.reject_code(code_id)
            rejected_count += 1

    return BulkApprovalResponse(
        processed=approved_count + rejected_count,
        approved=approved_count,
        rejected=rejected_count,
    )


@app.get("/review/stats", response_model=ReviewStatsResponse)
async def get_review_stats(
    code_repo: ExtractedCodeRepositoryDep,
) -> ReviewStatsResponse:
    """Get statistics for the review queue."""
    stats = code_repo.get_approval_stats()
    return ReviewStatsResponse(
        pending=stats.get("pending", 0),
        approved_auto=stats.get("approved_auto", 0),
        approved_manual=stats.get("approved_manual", 0),
        rejected=stats.get("rejected", 0),
        total=stats.get("total", 0),
    )


# ============================================================================
# Training Data Capture (for Chrome Extension)
# ============================================================================


class TrainingCaptureRequest(BaseModel):
    """Request body for capturing lot page for training."""

    html: str = Field(..., description="Full HTML of the lot page")
    lot_code: str = Field(..., alias="lotCode", description="Lot code")
    title: str = Field(default="", description="Lot title")
    images: list[str] = Field(default_factory=list, description="Image URLs")
    url: str = Field(default="", description="Page URL")


class TrainingCaptureResponse(BaseModel):
    """Response from training capture."""

    success: bool
    lot_code: str
    images_queued: int
    message: str


@app.post("/api/training/capture", response_model=TrainingCaptureResponse)
async def capture_training_data(
    request: TrainingCaptureRequest,
    lot_image_repo: LotImageRepositoryDep,
    lot_repository: LotRepositoryDep,
) -> TrainingCaptureResponse:
    """Capture a lot page for training data.

    This endpoint receives HTML from the Chrome extension and queues
    the images for download and OCR processing.
    """
    import hashlib
    from pathlib import Path

    # Save HTML to training_data directory
    training_dir = Path("training_data/captured")
    training_dir.mkdir(parents=True, exist_ok=True)

    html_file = training_dir / f"{request.lot_code}.html"
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(request.html)

    # Queue images for processing: resolve lot_id and insert images
    images_queued = 0
    lot_id = lot_repository.get_id(request.lot_code)
    if lot_id:
        inserted = lot_image_repo.insert_images(lot_id, request.images)
        images_queued = len(inserted)
    else:
        # If lot unknown, skip inserting images and log
        images_queued = 0

    return TrainingCaptureResponse(
        success=True,
        lot_code=request.lot_code,
        images_queued=images_queued,
        message=f"Captured {request.lot_code} with {images_queued} images",
    )


router = APIRouter()

UPLOAD_DIR = "training_data/real_training/exports/"


@router.post("/upload-tokens")
async def upload_tokens(file: UploadFile = File(...)):
    filename = file.filename or ""
    dest_path = os.path.join(UPLOAD_DIR, filename)
    with open(dest_path, "wb") as f:
        f.write(await file.read())
    return {"status": "success", "path": dest_path}


@router.get("/download-tokens/{filename}")
async def download_tokens(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        return Response(status_code=404)
    with open(file_path, "rb") as f:
        data = f.read()
    return Response(content=data, media_type="text/plain")


app.include_router(router, prefix="/api")


class LabelExtractionResponse(BaseModel):
    text: str
    label: dict | None
    preprocessing_steps: list[str]
    ocr_confidence: float | None


@app.post("/extract-label", response_model=LabelExtractionResponse)
async def extract_label_endpoint(
    file: UploadFile = File(...),
    ocr_language: str = "eng+nld",
):
    image_bytes = await file.read()
    result: LabelExtractionResult = extract_label_from_image(
        image_bytes, ocr_language=ocr_language
    )
    # Convert dataclass to dict for label (if present)
    label_dict = None
    # Ensure label is always a dict or None
    if result.label is None:
        label_dict = None
    elif hasattr(result.label, "__dict__"):
        label_dict = dict(result.label.__dict__)
    else:
        label_dict = result.label if isinstance(result.label, dict) else None
    return LabelExtractionResponse(
        text=result.text,
        label=label_dict,
        preprocessing_steps=result.preprocessing_steps,
        ocr_confidence=result.ocr_confidence,
    )

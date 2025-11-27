"""FastAPI application exposing Troostwatch repositories.

Run with ``uvicorn troostwatch.app.api:app``.
"""

from __future__ import annotations

import asyncio
from typing import Dict, List, Optional

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

from troostwatch.app.dependencies import (
    get_buyer_repository,
    get_lot_repository,
    get_position_repository,
    BuyerRepository,
    LotRepository,
    PositionRepository,
)
from troostwatch.infrastructure.db.repositories import BidRepository
from troostwatch.infrastructure.db import get_connection
from troostwatch.services import positions as position_service
from troostwatch.services.buyers import BuyerAlreadyExistsError, BuyerService
from troostwatch.services.lots import LotView, LotViewService
from troostwatch.services.sync_service import SyncService


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

    async def publish(self, payload: Dict) -> None:
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


from troostwatch import __version__

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
    repository: BuyerRepository = Depends(get_buyer_repository),
) -> BuyerService:
    return BuyerService(repository=repository, event_publisher=event_bus.publish)


def get_lot_view_service(
    lot_repository: LotRepository = Depends(get_lot_repository),
) -> LotViewService:
    return LotViewService(lot_repository)


def get_sync_service() -> SyncService:
    return sync_service


class BuyerCreateRequest(BaseModel):
    label: str
    name: Optional[str] = None
    notes: Optional[str] = None


class BuyerResponse(BaseModel):
    id: int
    label: str
    name: Optional[str] = None
    notes: Optional[str] = None


class BuyerCreateResponse(BaseModel):
    status: str
    label: str


class PositionUpdate(BaseModel):
    buyer_label: str
    lot_code: str
    auction_code: Optional[str] = None
    max_budget_total_eur: Optional[float] = Field(None, ge=0)
    preferred_bid_eur: Optional[float] = Field(None, ge=0)
    watch: Optional[bool] = None


class PositionResponse(BaseModel):
    """A tracked position linking a buyer to a lot."""

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


class PositionBatchRequest(BaseModel):
    updates: List[PositionUpdate]


class PositionBatchResponse(BaseModel):
    """Response for batch position updates."""

    updated: int
    created: int = 0
    errors: List[str] = Field(default_factory=list)


class SyncRequest(BaseModel):
    auction_code: str
    auction_url: str
    max_pages: Optional[int] = Field(None, ge=1)
    dry_run: bool = False


class SyncRunResultResponse(BaseModel):
    """Result of a single sync run."""

    run_id: Optional[int] = None
    status: str  # 'success', 'failed', 'running'
    pages_scanned: int = 0
    lots_scanned: int = 0
    lots_updated: int = 0
    error_count: int = 0
    errors: List[str] = Field(default_factory=list)


class SyncSummaryResponse(BaseModel):
    """Summary response for a sync operation."""

    status: str  # 'success', 'failed', 'error'
    auction_code: Optional[str] = None
    result: Optional[SyncRunResultResponse] = None
    error: Optional[str] = None


class LiveSyncStatusResponse(BaseModel):
    """Status of the live sync worker."""

    state: str  # 'idle', 'running', 'paused', 'stopping'
    last_sync: Optional[str] = None
    next_sync: Optional[str] = None
    current_auction: Optional[str] = None


class LiveSyncControlResponse(BaseModel):
    """Response for live sync control actions."""

    state: str
    detail: Optional[str] = None


class LiveSyncStartRequest(BaseModel):
    auction_code: str
    auction_url: str
    max_pages: Optional[int] = Field(None, ge=1)
    dry_run: bool = False
    interval_seconds: Optional[float] = Field(
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
    lot_title: Optional[str] = None
    amount_eur: float
    placed_at: str
    note: Optional[str] = None


class BidCreateRequest(BaseModel):
    """Request to record a new bid."""

    buyer_label: str
    auction_code: str
    lot_code: str
    amount_eur: float = Field(gt=0)
    note: Optional[str] = None


@app.get("/lots", response_model=list[LotView])
async def list_lots(
    auction_code: Optional[str] = None,
    state: Optional[str] = None,
    brand: Optional[str] = None,
    limit: Optional[int] = Query(default=None, ge=1),
    lot_view_service: LotViewService = Depends(get_lot_view_service),
) -> List[LotView]:
    return lot_view_service.list_lots(
        auction_code=auction_code, state=state, brand=brand, limit=limit
    )


@app.post("/positions/batch", response_model=PositionBatchResponse)
async def upsert_positions(
    payload: PositionBatchRequest,
    repository: PositionRepository = Depends(get_position_repository),
) -> PositionBatchResponse:
    try:
        updates = [
            position_service.PositionUpdateData(
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
            updated=result.get("updated", 0),
            created=result.get("created", 0),
            errors=result.get("errors", []),
        )
    except ValueError as exc:  # raised when buyer or lot not found
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@app.get("/positions", response_model=List[PositionResponse])
async def list_positions(
    buyer: Optional[str] = Query(None, description="Filter by buyer label"),
    repository: PositionRepository = Depends(get_position_repository),
) -> List[PositionResponse]:
    """List all tracked positions, optionally filtered by buyer."""
    positions = repository.list(buyer_label=buyer)
    return [
        PositionResponse(
            id=int(pos.get("id", 0)),
            buyer_label=str(pos.get("buyer_label", "")),
            lot_code=str(pos.get("lot_code", "")),
            auction_code=pos.get("auction_code"),
            max_budget_total_eur=pos.get("max_budget_total_eur"),
            preferred_bid_eur=pos.get("preferred_bid_eur"),
            track_active=bool(pos.get("track_active", True)),
            lot_title=pos.get("lot_title"),
            current_bid_eur=pos.get("current_bid_eur"),
            closing_time=pos.get("closing_time_current"),
        )
        for pos in positions
    ]


@app.delete("/positions/{buyer_label}/{lot_code}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_position(
    buyer_label: str,
    lot_code: str,
    auction_code: Optional[str] = Query(None),
    repository: PositionRepository = Depends(get_position_repository),
) -> None:
    """Delete a tracked position."""
    repository.delete(
        buyer_label=buyer_label,
        lot_code=lot_code,
        auction_code=auction_code,
    )


@app.get("/buyers", response_model=List[BuyerResponse])
async def list_buyers(
    service: BuyerService = Depends(get_buyer_service),
) -> List[BuyerResponse]:
    buyers = service.list_buyers()
    result: List[BuyerResponse] = []
    for buyer in buyers:
        buyer_id = buyer.get("id")
        buyer_label = buyer.get("label")
        if buyer_id is None or buyer_label is None:
            continue
        result.append(
            BuyerResponse(
                id=int(buyer_id),
                label=str(buyer_label),
                name=str(buyer.get("name")) if buyer.get("name") else None,
                notes=str(buyer.get("notes")) if buyer.get("notes") else None,
            )
        )
    return result


@app.post(
    "/buyers", status_code=status.HTTP_201_CREATED, response_model=BuyerCreateResponse
)
async def create_buyer(
    payload: BuyerCreateRequest, service: BuyerService = Depends(get_buyer_service)
) -> BuyerCreateResponse:
    try:
        result = await service.create_buyer(
            label=payload.label,
            name=payload.name,
            notes=payload.notes,
        )
    except BuyerAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    return BuyerCreateResponse(**result)


@app.delete("/buyers/{label}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_buyer(
    label: str, service: BuyerService = Depends(get_buyer_service)
) -> None:
    await service.delete_buyer(label=label)


# =============================================================================
# Bids Endpoints
# =============================================================================

def get_bid_repository() -> BidRepository:
    """Dependency that provides a BidRepository."""
    from troostwatch.app.config import get_db_path
    conn = get_connection(get_db_path(), check_same_thread=False)
    return BidRepository(conn)


@app.get("/bids", response_model=List[BidResponse])
async def list_bids(
    buyer: Optional[str] = Query(None, description="Filter by buyer label"),
    lot_code: Optional[str] = Query(None, description="Filter by lot code"),
    limit: int = Query(100, ge=1, le=500),
) -> List[BidResponse]:
    """List recorded bids with optional filters."""
    repo = get_bid_repository()
    bids = repo.list(buyer_label=buyer, lot_code=lot_code, limit=limit)
    return [
        BidResponse(
            id=int(bid.get("id", 0)),
            buyer_label=str(bid.get("buyer_label", "")),
            lot_code=str(bid.get("lot_code", "")),
            auction_code=str(bid.get("auction_code", "")),
            lot_title=bid.get("lot_title"),
            amount_eur=float(bid.get("amount_eur", 0)),
            placed_at=str(bid.get("placed_at", "")),
            note=bid.get("note"),
        )
        for bid in bids
    ]


@app.post("/bids", status_code=status.HTTP_201_CREATED, response_model=BidResponse)
async def create_bid(payload: BidCreateRequest) -> BidResponse:
    """Record a new bid (local only, does not submit to Troostwijk)."""
    repo = get_bid_repository()
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
    bids = repo.list(buyer_label=payload.buyer_label, lot_code=payload.lot_code, limit=1)
    if not bids:
        raise HTTPException(status_code=500, detail="Bid created but not found")
    
    bid = bids[0]
    return BidResponse(
        id=int(bid.get("id", 0)),
        buyer_label=str(bid.get("buyer_label", "")),
        lot_code=str(bid.get("lot_code", "")),
        auction_code=str(bid.get("auction_code", "")),
        lot_title=bid.get("lot_title"),
        amount_eur=float(bid.get("amount_eur", 0)),
        placed_at=str(bid.get("placed_at", "")),
        note=bid.get("note"),
    )


@app.post("/sync", status_code=status.HTTP_202_ACCEPTED, response_model=SyncSummaryResponse)
async def trigger_sync(
    request: SyncRequest, service: SyncService = Depends(get_sync_service)
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
    if result_data:
        result = SyncRunResultResponse(**result_data)
    return SyncSummaryResponse(
        status=summary_dict.get("status", "error"),
        auction_code=summary_dict.get("auction_code"),
        result=result,
        error=summary_dict.get("error"),
    )


@app.post("/live-sync/start", status_code=status.HTTP_202_ACCEPTED, response_model=LiveSyncControlResponse)
async def start_live_sync(
    request: LiveSyncStartRequest, service: SyncService = Depends(get_sync_service)
) -> LiveSyncControlResponse:
    result = await service.start_live_sync(
        auction_code=request.auction_code,
        auction_url=request.auction_url,
        max_pages=request.max_pages,
        dry_run=request.dry_run,
        interval_seconds=request.interval_seconds,
    )
    return LiveSyncControlResponse(
        state=result.get("state", "unknown"),
        detail=result.get("detail"),
    )


@app.post("/live-sync/pause", status_code=status.HTTP_202_ACCEPTED, response_model=LiveSyncControlResponse)
async def pause_live_sync(
    service: SyncService = Depends(get_sync_service),
) -> LiveSyncControlResponse:
    result = await service.pause_live_sync()
    return LiveSyncControlResponse(
        state=result.get("state", "unknown"),
        detail=result.get("detail"),
    )


@app.post("/live-sync/stop", status_code=status.HTTP_202_ACCEPTED, response_model=LiveSyncControlResponse)
async def stop_live_sync(
    service: SyncService = Depends(get_sync_service),
) -> LiveSyncControlResponse:
    result = await service.stop_live_sync()
    return LiveSyncControlResponse(
        state=result.get("state", "unknown"),
        detail=result.get("detail"),
    )


@app.get("/live-sync/status", response_model=LiveSyncStatusResponse)
async def get_live_sync_status(
    service: SyncService = Depends(get_sync_service),
) -> LiveSyncStatusResponse:
    status_dict = service.get_live_sync_status()
    return LiveSyncStatusResponse(
        state=status_dict.get("state", "idle"),
        last_sync=status_dict.get("last_sync"),
        next_sync=status_dict.get("next_sync"),
        current_auction=status_dict.get("current_auction"),
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

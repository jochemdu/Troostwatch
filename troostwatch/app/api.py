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
from pydantic import BaseModel, Field

from troostwatch.app.dependencies import (
    get_buyer_repository,
    get_lot_repository,
    get_position_repository,
    BuyerRepository,
    LotRepository,
    PositionRepository,
)
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

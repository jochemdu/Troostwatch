"""FastAPI application exposing Troostwatch repositories.

Run with ``uvicorn troostwatch.app.api:app``.
"""

from __future__ import annotations

import asyncio
from typing import Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field

from troostwatch.app.dependencies import (
    get_buyer_repository,
    get_lot_repository,
    get_position_repository,
)
from troostwatch.infrastructure.db.repositories import BuyerRepository, LotRepository, PositionRepository
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


event_bus = LotEventBus()
sync_service = SyncService(event_publisher=event_bus.publish)
app = FastAPI(title="Troostwatch API", version="0.1.0")


def get_buyer_service(repository: BuyerRepository = Depends(get_buyer_repository)) -> BuyerService:
    return BuyerService(repository=repository, event_publisher=event_bus.publish)


def get_lot_view_service(lot_repository: LotRepository = Depends(get_lot_repository)) -> LotViewService:
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


class SyncRequest(BaseModel):
    auction_code: str
    auction_url: str
    max_pages: Optional[int] = Field(None, ge=1)
    dry_run: bool = False


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
    limit: Optional[int] = Query(default=None, ge=1),
    lot_view_service: LotViewService = Depends(get_lot_view_service),
) -> List[LotView]:
    return lot_view_service.list_lots(auction_code=auction_code, state=state, limit=limit)


@app.post("/positions/batch")
async def upsert_positions(
    payload: PositionBatchRequest,
    repository: PositionRepository = Depends(get_position_repository),
) -> Dict[str, object]:
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
        return await position_service.upsert_positions(
            repository=repository, updates=updates, event_publisher=event_bus.publish
        )
    except ValueError as exc:  # raised when buyer or lot not found
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@app.get("/buyers", response_model=List[BuyerResponse])
async def list_buyers(service: BuyerService = Depends(get_buyer_service)) -> List[BuyerResponse]:
    buyers = service.list_buyers()
    return [BuyerResponse(**buyer) for buyer in buyers]


@app.post("/buyers", status_code=status.HTTP_201_CREATED, response_model=BuyerCreateResponse)
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
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return BuyerCreateResponse(**result)


@app.delete("/buyers/{label}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_buyer(label: str, service: BuyerService = Depends(get_buyer_service)) -> None:
    await service.delete_buyer(label=label)


@app.post("/sync", status_code=status.HTTP_202_ACCEPTED)
async def trigger_sync(request: SyncRequest, service: SyncService = Depends(get_sync_service)) -> Dict[str, object]:
    return await service.run_sync(
        auction_code=request.auction_code,
        auction_url=request.auction_url,
        max_pages=request.max_pages,
        dry_run=request.dry_run,
    )


@app.post("/live-sync/start", status_code=status.HTTP_202_ACCEPTED)
async def start_live_sync(request: LiveSyncStartRequest, service: SyncService = Depends(get_sync_service)) -> Dict[str, object]:
    return await service.start_live_sync(
        auction_code=request.auction_code,
        auction_url=request.auction_url,
        max_pages=request.max_pages,
        dry_run=request.dry_run,
        interval_seconds=request.interval_seconds,
    )


@app.post("/live-sync/pause", status_code=status.HTTP_202_ACCEPTED)
async def pause_live_sync(service: SyncService = Depends(get_sync_service)) -> Dict[str, object]:
    return await service.pause_live_sync()


@app.post("/live-sync/stop", status_code=status.HTTP_202_ACCEPTED)
async def stop_live_sync(service: SyncService = Depends(get_sync_service)) -> Dict[str, object]:
    return await service.stop_live_sync()


@app.get("/live-sync/status")
async def get_live_sync_status(service: SyncService = Depends(get_sync_service)) -> Dict[str, object]:
    return service.get_live_sync_status()


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

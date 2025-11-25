"""FastAPI application exposing Troostwatch repositories.

Run with ``uvicorn troostwatch.app.api:app``.
"""

from __future__ import annotations

import asyncio
import sqlite3
from dataclasses import asdict
from typing import Dict, Iterator, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field

from troostwatch.infrastructure.db import ensure_schema, get_connection
from troostwatch.infrastructure.db.config import get_path_config
from troostwatch.infrastructure.db.repositories import BuyerRepository, LotRepository, PositionRepository
from troostwatch.infrastructure.db.repositories.buyers import DuplicateBuyerError
from troostwatch.services.live_runner import LiveSyncConfig, LiveSyncRunner
from troostwatch.services.sync import sync as sync_service


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
app = FastAPI(title="Troostwatch API", version="0.1.0")
live_sync_runner = LiveSyncRunner(db_path=str(get_path_config()["db_path"]), event_publisher=event_bus.publish)


def get_db_connection() -> Iterator[sqlite3.Connection]:
    """Provide a SQLite connection with the required schema ensured."""

    with get_connection() as conn:
        ensure_schema(conn)
        yield conn


def get_lot_repository(conn: sqlite3.Connection = Depends(get_db_connection)) -> LotRepository:
    return LotRepository(conn)


def get_buyer_repository(conn: sqlite3.Connection = Depends(get_db_connection)) -> BuyerRepository:
    return BuyerRepository(conn)


def get_position_repository(conn: sqlite3.Connection = Depends(get_db_connection)) -> PositionRepository:
    return PositionRepository(conn)


class BuyerCreateRequest(BaseModel):
    label: str
    name: Optional[str] = None
    notes: Optional[str] = None


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


@app.get("/lots")
async def list_lots(
    auction_code: Optional[str] = None,
    state: Optional[str] = None,
    limit: Optional[int] = Query(default=None, ge=1),
    repository: LotRepository = Depends(get_lot_repository),
) -> List[Dict[str, Optional[str]]]:
    return repository.list_lots(auction_code=auction_code, state=state, limit=limit)


@app.post("/positions/batch")
async def upsert_positions(
    payload: PositionBatchRequest,
    repository: PositionRepository = Depends(get_position_repository),
) -> Dict[str, object]:
    processed: list[dict] = []
    for update in payload.updates:
        try:
            repository.upsert(
                buyer_label=update.buyer_label,
                lot_code=update.lot_code,
                auction_code=update.auction_code,
                track_active=True if update.watch is None else update.watch,
                max_budget_total_eur=update.max_budget_total_eur,
                my_highest_bid_eur=update.preferred_bid_eur,
            )
            processed.append(update.dict())
        except ValueError as exc:  # raised when buyer or lot not found
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await event_bus.publish({"type": "positions_updated", "count": len(processed), "items": processed})
    return {"updated": len(processed)}


@app.get("/buyers")
async def list_buyers(repository: BuyerRepository = Depends(get_buyer_repository)) -> List[Dict[str, Optional[str]]]:
    return repository.list()


@app.post("/buyers", status_code=status.HTTP_201_CREATED)
async def create_buyer(payload: BuyerCreateRequest, repository: BuyerRepository = Depends(get_buyer_repository)) -> Dict[str, str]:
    try:
        repository.add(payload.label, payload.name, payload.notes)
    except DuplicateBuyerError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    await event_bus.publish({"type": "buyer_created", "label": payload.label})
    return {"status": "created", "label": payload.label}


@app.delete("/buyers/{label}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_buyer(label: str, repository: BuyerRepository = Depends(get_buyer_repository)) -> None:
    repository.delete(label)
    await event_bus.publish({"type": "buyer_deleted", "label": label})


@app.post("/sync", status_code=status.HTTP_202_ACCEPTED)
async def trigger_sync(request: SyncRequest) -> Dict[str, object]:
    db_path = str(get_path_config()["db_path"])

    result = await asyncio.to_thread(
        sync_service.sync_auction_to_db,
        db_path=db_path,
        auction_code=request.auction_code,
        auction_url=request.auction_url,
        max_pages=request.max_pages,
        dry_run=request.dry_run,
    )

    payload = {"type": "sync_finished", "auction_code": request.auction_code, "result": asdict(result)}
    await event_bus.publish(payload)
    return payload


@app.post("/live-sync/start", status_code=status.HTTP_202_ACCEPTED)
async def start_live_sync(request: LiveSyncStartRequest) -> Dict[str, object]:
    state = await live_sync_runner.start(
        LiveSyncConfig(
            auction_code=request.auction_code,
            auction_url=request.auction_url,
            max_pages=request.max_pages,
            dry_run=request.dry_run,
            interval_seconds=request.interval_seconds,
        )
    )
    return {"status": state.status, "state": state.to_dict()}


@app.post("/live-sync/pause", status_code=status.HTTP_202_ACCEPTED)
async def pause_live_sync() -> Dict[str, object]:
    state = await live_sync_runner.pause()
    return {"status": state.status, "state": state.to_dict()}


@app.post("/live-sync/stop", status_code=status.HTTP_202_ACCEPTED)
async def stop_live_sync() -> Dict[str, object]:
    state = await live_sync_runner.stop()
    return {"status": state.status, "state": state.to_dict()}


@app.get("/live-sync/status")
async def get_live_sync_status() -> Dict[str, object]:
    return live_sync_runner.get_status()


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

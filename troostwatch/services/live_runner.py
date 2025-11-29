"""Live sync runner that executes auction syncs on an interval.

This worker coordinates repeated runs of :func:`sync_auction_to_db` and
publishes lifecycle events to the WebSocket layer so the UI can stay up to
date. It keeps lightweight state in memory while persisting run details via
``sync_runs`` records written by the sync routine itself.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Literal

from troostwatch.infrastructure.db import iso_utcnow
from troostwatch.infrastructure.observability import get_logger
from troostwatch.services.dto import EventPublisher
from troostwatch.services.sync import SyncRunResult, sync_auction_to_db

SyncCallable = Callable[..., SyncRunResult]
LiveSyncStatus = Literal["idle", "running", "paused", "stopping"]


@dataclass
class LiveSyncConfig:
    """Configuration for a live sync loop."""

    auction_code: str
    auction_url: str
    max_pages: int | None = None
    dry_run: bool = False
    interval_seconds: float | None = None


@dataclass
class LiveSyncState:
    """Current state snapshot for the live sync runner."""

    status: LiveSyncStatus = "idle"
    current_run_started_at: str | None = None
    last_result: SyncRunResult | None = None
    last_error: str | None = None
    config: LiveSyncConfig | None = None
    paused_at: str | None = None

    def to_dict(self) -> dict:
        payload = asdict(self)
        if self.last_result is not None:
            payload["last_result"] = asdict(self.last_result)
        return payload


class LiveSyncRunner:
    """Background worker that repeatedly triggers sync runs."""

    def __init__(
        self,
        *,
        db_path: str,
        event_publisher: EventPublisher,
        sync_callable: SyncCallable = sync_auction_to_db,
        default_interval_seconds: float = 60.0,
    ) -> None:
        self._db_path = db_path
        self._event_publisher = event_publisher
        self._sync_callable = sync_callable
        self._default_interval_seconds = default_interval_seconds
        self._logger = get_logger(__name__)

        self._state = LiveSyncState()
        self._task: asyncio.Task | None = None
        self._lock = asyncio.Lock()
        self._pause_event = asyncio.Event()
        self._stop_event = asyncio.Event()
        self._pause_event.set()

    @property
    def state(self) -> LiveSyncState:
        return self._state

    async def start(self, config: LiveSyncConfig) -> LiveSyncState:
        """Start or resume the live sync worker."""

        async with self._lock:
            self._state.config = config
            self._state.last_error = None
            self._state.paused_at = None
            self._stop_event.clear()
            self._pause_event.set()

            if self._task and not self._task.done() and self._state.status == "running":
                raise RuntimeError("Live sync is already running")

            if self._task is None or self._task.done():
                self._task = asyncio.create_task(self._run_loop())

            await self._set_status("running", log_message="Live sync started")
            return self._state

    async def pause(self) -> LiveSyncState:
        """Pause the live sync worker until resumed."""

        async with self._lock:
            if self._task is None or self._task.done():
                return self._state
            self._pause_event.clear()
            self._state.paused_at = iso_utcnow()
            await self._set_status("paused", log_message="Live sync paused")
            return self._state

    async def stop(self) -> LiveSyncState:
        """Stop the live sync worker and wait for the loop to exit."""

        async with self._lock:
            self._stop_event.set()
            self._pause_event.set()
            await self._set_status("stopping", log_message="Stopping live sync")

        if self._task is not None:
            await self._task

        async with self._lock:
            await self._set_status("idle", log_message="Live sync stopped")
            self._task = None
            return self._state

    def get_status(self) -> dict:
        return self._state.to_dict()

    def _resolved_interval(self) -> float | None:
        if self._state.config is None:
            return None
        if self._state.config.interval_seconds is None:
            return self._default_interval_seconds
        return self._state.config.interval_seconds

    async def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            await self._pause_event.wait()
            if self._stop_event.is_set():
                break

            config = self._state.config
            if config is None:
                self._logger.error("Live sync loop started without config")
                break

            await self._set_status("running")
            self._state.current_run_started_at = iso_utcnow()
            await self._emit_log(
                "Starting sync for {} at {}".format(config.auction_code, config.auction_url)
            )

            try:
                result = await asyncio.to_thread(
                    self._sync_callable,
                    self._db_path,
                    auction_code=config.auction_code,
                    auction_url=config.auction_url,
                    max_pages=config.max_pages,
                    dry_run=config.dry_run,
                )
                self._state.last_result = result
                self._state.last_error = None
                await self._publish_event(
                    {
                        "type": "live_sync_result",
                        "status": result.status,
                        "auction_code": config.auction_code,
                        "payload": asdict(result),
                    }
                )
                if result.errors:
                    for err in result.errors:
                        await self._emit_log("Sync error: {}".format(err))
                await self._emit_log(
                    "Sync finished with {} updates across {} lots".format(result.lots_updated, result.lots_scanned)
                )
            except Exception as exc:  # pragma: no cover - defensive logging
                message = "Live sync failed: {}".format(exc)
                self._logger.exception(message)
                self._state.last_error = str(exc)
                await self._publish_event(
                    {
                        "type": "live_sync_error",
                        "message": str(exc),
                        "time": iso_utcnow(),
                    }
                )
                await self._emit_log(message)

            interval = self._resolved_interval()
            if interval is None or interval <= 0:
                break

            try:
                await asyncio.wait_for(self._wait_with_pause(), timeout=interval)
            except asyncio.TimeoutError:
                continue

        await self._publish_idle()

    async def _wait_with_pause(self) -> None:
        while not self._stop_event.is_set():
            try:
                await asyncio.wait_for(self._pause_event.wait(), timeout=0.2)
            except asyncio.TimeoutError:
                continue
            if self._pause_event.is_set():
                return

    async def _publish_idle(self) -> None:
        async with self._lock:
            self._state.status = "idle"
            await self._publish_event(
                {
                    "type": "live_sync_status",
                    "status": self._state.status,
                    "time": iso_utcnow(),
                    "state": self.get_status(),
                }
            )

    async def _publish_event(self, payload: dict) -> None:
        try:
            await self._event_publisher(payload)
        except Exception:  # pragma: no cover - isolate websocket errors
            self._logger.exception("Failed to publish live sync event")

    async def _emit_log(self, message: str) -> None:
        self._logger.info(message)
        await self._publish_event(
            {
                "type": "live_sync_log",
                "message": message,
                "time": iso_utcnow(),
            }
        )

    async def _set_status(
        self, status: LiveSyncStatus, *, log_message: str | None = None
    ) -> None:
        self._state.status = status
        await self._publish_event(
            {
                "type": "live_sync_status",
                "status": status,
                "time": iso_utcnow(),
                "state": self.get_status(),
            }
        )
        if log_message:
            await self._emit_log(log_message)

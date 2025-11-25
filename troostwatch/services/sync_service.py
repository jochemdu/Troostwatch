from __future__ import annotations

from typing import Awaitable, Callable, Dict, List, Optional

from troostwatch.infrastructure.db import ensure_core_schema, ensure_schema, get_connection, get_path_config
from troostwatch.infrastructure.db.repositories import AuctionRepository
from troostwatch.services.live_runner import LiveSyncConfig, LiveSyncRunner, LiveSyncState
from troostwatch.services.sync import sync_auction

EventPublisher = Callable[[dict[str, object]], Awaitable[None]]


async def _noop_event(_: dict[str, object]) -> None:
    """Default event publisher when none is provided."""


class SyncService:
    """Coordinate auction sync workflows and live sync runner state."""

    def __init__(
        self,
        *,
        db_path: str | None = None,
        event_publisher: EventPublisher | None = None,
        live_sync_runner: LiveSyncRunner | None = None,
    ) -> None:
        self._db_path = db_path or str(get_path_config()["db_path"])
        self._event_publisher = event_publisher or _noop_event
        self._live_sync_runner = live_sync_runner or LiveSyncRunner(
            db_path=self._db_path, event_publisher=self._event_publisher
        )

    async def run_sync(
        self,
        *,
        auction_code: str,
        auction_url: str,
        max_pages: Optional[int] = None,
        dry_run: bool = False,
    ) -> Dict[str, object]:
        """Run a one-off sync for a single auction."""

        return await sync_auction(
            db_path=self._db_path,
            auction_code=auction_code,
            auction_url=auction_url,
            max_pages=max_pages,
            dry_run=dry_run,
            event_publisher=self._event_publisher,
        )

    async def run_multi_sync(
        self,
        *,
        include_inactive: bool = False,
        max_pages: int | None = None,
        dry_run: bool = False,
    ) -> List[Dict[str, object]]:
        """Synchronize all auctions stored locally."""

        auctions = self._load_auctions(include_inactive=include_inactive)
        results: list[dict[str, object]] = []
        for auction in auctions:
            code = auction.get("auction_code") or auction.get("code")
            url = auction.get("url")
            if not code or not url:
                results.append(
                    {
                        "status": "skipped",
                        "reason": "missing auction_code or url",
                        "auction": auction,
                    }
                )
                continue
            results.append(
                await self.run_sync(
                    auction_code=code,
                    auction_url=url,
                    max_pages=max_pages,
                    dry_run=dry_run,
                )
            )
        return results

    async def start_live_sync(
        self,
        *,
        auction_code: str,
        auction_url: str,
        max_pages: int | None = None,
        dry_run: bool = False,
        interval_seconds: float | None = None,
    ) -> Dict[str, object]:
        state = await self._live_sync_runner.start(
            LiveSyncConfig(
                auction_code=auction_code,
                auction_url=auction_url,
                max_pages=max_pages,
                dry_run=dry_run,
                interval_seconds=interval_seconds,
            )
        )
        return self._format_live_state(state)

    async def pause_live_sync(self) -> Dict[str, object]:
        state = await self._live_sync_runner.pause()
        return self._format_live_state(state)

    async def stop_live_sync(self) -> Dict[str, object]:
        state = await self._live_sync_runner.stop()
        return self._format_live_state(state)

    def get_live_sync_status(self) -> Dict:
        return self._live_sync_runner.get_status()

    def _format_live_state(self, state: LiveSyncState) -> Dict[str, object]:
        return {"status": state.status, "state": state.to_dict()}

    def _load_auctions(self, *, include_inactive: bool) -> list[dict[str, object]]:
        with get_connection(self._db_path) as conn:
            ensure_core_schema(conn)
            ensure_schema(conn)
            repository = AuctionRepository(conn)
            return repository.list(only_active=not include_inactive)

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass

from troostwatch.infrastructure.http import TroostwatchHttpClient
from troostwatch.infrastructure.db import (
    ensure_core_schema,
    ensure_schema,
    get_connection,
    get_path_config,
)
from troostwatch.infrastructure.db.repositories import (
    AuctionRepository,
    PreferenceRepository,
)
from troostwatch.infrastructure.observability import get_logger
from troostwatch.services.dto import EventPublisher, noop_event_publisher
from troostwatch.services.live_runner import (
    LiveSyncConfig,
    LiveSyncRunner,
    LiveSyncState,
)
from troostwatch.services.sync import SyncRunResult, sync_auction_to_db


@dataclass(frozen=True)
class AuctionSelection:
    """Result of resolving an auction for synchronization."""

    resolved_code: str | None
    resolved_url: str | None
    available: list[dict[str, str | None]]
    preferred_index: int | None

    @property
    def default_choice_number(self) -> int | None:
        if not self.available:
            return None
        index = self.preferred_index if self.preferred_index is not None else 0
        return index + 1


@dataclass(frozen=True)
class SyncRunSummary:
    """Structured result for a sync execution."""

    status: str
    auction_code: str | None = None
    result: SyncRunResult | None = None
    error: str | None = None

    def to_event_payload(self, auction_code: str | None = None) -> dict[str, object]:
        code = auction_code or self.auction_code
        payload: dict[str, object] = {"type": "sync_finished", "status": self.status}
        if code:
            payload["auction_code"] = code
        if self.result:
            payload["result"] = asdict(self.result)
        if self.error:
            payload["error"] = self.error
        return payload

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {"type": "sync_finished", "status": self.status}
        if self.auction_code:
            payload["auction_code"] = self.auction_code
        if self.result:
            payload["result"] = asdict(self.result)
        if self.error:
            payload["error"] = self.error
        return payload


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
        self._event_publisher = event_publisher or noop_event_publisher
        self._live_sync_runner = live_sync_runner or LiveSyncRunner(
            db_path=self._db_path, event_publisher=self._event_publisher
        )
        self._logger = get_logger(__name__)

    async def run_sync(
        self,
        *,
        auction_code: str,
        auction_url: str,
        max_pages: int | None = None,
        dry_run: bool = False,
        delay_seconds: float | None = None,
        max_concurrent_requests: int = 5,
        throttle_per_host: float | None = None,
        max_retries: int = 3,
        retry_backoff_base: float = 0.5,
        concurrency_mode: str = "asyncio",
        force_detail_refetch: bool = False,
        verbose: bool | None = None,
        log_path: str | None = None,
        http_client: TroostwatchHttpClient | None = None,
    ) -> SyncRunSummary:
        """Run a one-off sync for a single auction."""
        self._logger.info(
            "Starting sync for auction %s (dry_run=%s, max_pages=%s)",
            auction_code,
            dry_run,
            max_pages,
        )

        try:
            result = await asyncio.to_thread(
                sync_auction_to_db,
                db_path=self._db_path,
                auction_code=auction_code,
                auction_url=auction_url,
                max_pages=max_pages,
                dry_run=dry_run,
                delay_seconds=delay_seconds,
                max_concurrent_requests=max_concurrent_requests,
                throttle_per_host=throttle_per_host,
                max_retries=max_retries,
                retry_backoff_base=retry_backoff_base,
                concurrency_mode=concurrency_mode,
                force_detail_refetch=force_detail_refetch,
                verbose=verbose,
                log_path=log_path,
                http_client=http_client,
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            self._logger.error("Sync failed for auction %s: %s", auction_code, exc)
            return SyncRunSummary(
                status="error", auction_code=auction_code, result=None, error=str(exc)
            )

        summary = SyncRunSummary(
            status=result.status,
            auction_code=auction_code,
            result=result,
            error=(
                "; ".join(result.errors)
                if result.status != "success" and result.errors
                else None
            ),
        )
        self._logger.info(
            "Sync completed for auction %s: status=%s, lots_scanned=%d, lots_updated=%d",
            auction_code,
            result.status,
            result.lots_scanned,
            result.lots_updated,
        )
        await self._event_publisher(summary.to_event_payload())
        return summary

    async def run_multi_sync(
        self,
        *,
        include_inactive: bool = False,
        max_pages: int | None = None,
        dry_run: bool = False,
    ) -> list[SyncRunSummary]:
        """Synchronize all auctions stored locally."""

        auctions = self._load_auctions(include_inactive=include_inactive)
        self._logger.info(
            "Starting multi-sync for %d auctions (include_inactive=%s)",
            len(auctions),
            include_inactive,
        )
        results: list[SyncRunSummary] = []
        for auction in auctions:
            code = auction.get("auction_code") or auction.get("code")
            url = auction.get("url")
            if not code or not url:
                results.append(
                    SyncRunSummary(
                        status="skipped",
                        result=None,
                        error="missing auction_code or url",
                    )
                )
                continue
            results.append(
                await self.run_sync(
                    auction_code=str(code),
                    auction_url=str(url),
                    max_pages=max_pages,
                    dry_run=dry_run,
                )
            )
        self._logger.info("Multi-sync completed: %d auctions processed", len(results))
        return results

    def choose_auction(
        self, *, auction_code: str | None = None, auction_url: str | None = None
    ) -> AuctionSelection:
        """Resolve which auction to sync using stored auctions and preferences."""
        self._logger.debug(
            "Choosing auction: code=%s, url=%s", auction_code, auction_url
        )

        available, preferred_code = self._load_auctions_and_preference(
            include_inactive=True
        )
        preferred_index: int | None = None
        if available:
            preferred_index = next(
                (
                    idx
                    for idx, auction in enumerate(available)
                    if auction.get("auction_code") == preferred_code
                ),
                None,
            )
            if preferred_index is None:
                preferred_index = 0

        resolved_code: str | None = auction_code
        if not resolved_code and preferred_index is not None:
            code_val = available[preferred_index].get("auction_code")
            resolved_code = str(code_val) if code_val else None

        resolved_url: str | None = auction_url
        if resolved_code and not resolved_url:
            match = next(
                (a for a in available if a.get("auction_code") == resolved_code), None
            )
            if match:
                url_val = match.get("url")
                resolved_url = str(url_val) if url_val else resolved_url

        return AuctionSelection(
            resolved_code=resolved_code,
            resolved_url=resolved_url,
            available=available,
            preferred_index=preferred_index,
        )

    async def start_live_sync(
        self,
        *,
        auction_code: str,
        auction_url: str,
        max_pages: int | None = None,
        dry_run: bool = False,
        interval_seconds: float | None = None,
    ) -> dict[str, object]:
        self._logger.info(
            "Starting live sync for auction %s (interval=%s)",
            auction_code,
            interval_seconds,
        )
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

    async def pause_live_sync(self) -> dict[str, object]:
        self._logger.info("Pausing live sync")
        state = await self._live_sync_runner.pause()
        return self._format_live_state(state)

    async def stop_live_sync(self) -> dict[str, object]:
        self._logger.info("Stopping live sync")
        state = await self._live_sync_runner.stop()
        return self._format_live_state(state)

    def get_live_sync_status(self) -> dict[str, object]:
        return self._live_sync_runner.get_status()

    def _format_live_state(self, state: LiveSyncState) -> dict[str, object]:
        return {"state": state.status, "detail": None}

    def _load_auctions(self, *, include_inactive: bool) -> list[dict[str, str | None]]:
        with get_connection(self._db_path) as conn:
            ensure_core_schema(conn)
            ensure_schema(conn)
            repository = AuctionRepository(conn)
            return repository.list(only_active=not include_inactive)

    def _load_auctions_and_preference(
        self, *, include_inactive: bool
    ) -> tuple[list[dict[str, str | None]], str | None]:
        with get_connection(self._db_path) as conn:
            ensure_core_schema(conn)
            ensure_schema(conn)
            auction_repo = AuctionRepository(conn)
            preference_repo = PreferenceRepository(conn)
            return auction_repo.list(
                only_active=not include_inactive
            ), preference_repo.get("preferred_auction")

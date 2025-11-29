import asyncio
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from troostwatch.services.live_runner import LiveSyncConfig, LiveSyncRunner
from troostwatch.services.sync import SyncRunResult


class StubSync:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, db_path: str, **_kwargs) -> SyncRunResult:  # pragma: no cover - exercised via runner
        self.calls += 1
        return SyncRunResult(
            run_id=self.calls,
            status="completed",
            pages_scanned=1,
            lots_scanned=1,
            lots_updated=1,
            error_count=0,
            errors=[],
        )


def test_live_runner_runs_once_and_emits_events(tmp_path: Path) -> None:
    events: list[dict] = []

    async def publish(payload: dict) -> None:
        events.append(payload)

    async def run() -> None:
        sync = StubSync()
        runner = LiveSyncRunner(
            db_path=str(tmp_path / "sync.db"),
            event_publisher=publish,
            sync_callable=sync,
            default_interval_seconds=0.1,
        )

        await runner.start(
            LiveSyncConfig(
                auction_code="A1-TEST",
                auction_url="https://example.com/a",
                interval_seconds=0,
            )
        )
        await asyncio.sleep(0.05)
        await runner.stop()

        assert sync.calls == 1
        assert any(evt.get("type") == "live_sync_result" for evt in events)

    asyncio.run(run())


def test_live_runner_pause_and_resume(tmp_path: Path) -> None:
    events: list[dict] = []

    async def publish(payload: dict) -> None:
        events.append(payload)

    async def run() -> None:
        sync = StubSync()
        runner = LiveSyncRunner(
            db_path=str(tmp_path / "sync.db"),
            event_publisher=publish,
            sync_callable=sync,
            default_interval_seconds=0.02,
        )
        config = LiveSyncConfig(
            auction_code="A1-TEST",
            auction_url="https://example.com/a",
            interval_seconds=0.02,
        )

        await runner.start(config)
        await asyncio.sleep(0.05)
        await runner.pause()
        await asyncio.sleep(0.05)
        paused_calls = sync.calls

        await asyncio.sleep(0.05)
        assert sync.calls == paused_calls

        await runner.start(config)
        await asyncio.sleep(0.05)
        await runner.stop()

        assert sync.calls > paused_calls
        assert any(evt.get("type") == "live_sync_status" for evt in events)

    asyncio.run(run())

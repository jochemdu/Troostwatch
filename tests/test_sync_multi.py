import asyncio
from dataclasses import dataclass

from click.testing import CliRunner

from troostwatch.interfaces.cli.sync_multi import sync_multi
from troostwatch.infrastructure.db import ensure_core_schema, ensure_schema, get_connection
from troostwatch.services.sync.sync import _upsert_auction
from troostwatch.services.sync_service import SyncRunSummary, SyncService


@dataclass
class DummyResult:
    run_id: int = 1
    status: str = "success"
    pages_scanned: int = 0
    lots_scanned: int = 0
    lots_updated: int = 0
    error_count: int = 0
    errors: list = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


def test_sync_multi_uses_db_auctions(monkeypatch, tmp_path):
    db_path = tmp_path / "sync_multi.db"
    with get_connection(db_path) as conn:
        ensure_core_schema(conn)
        ensure_schema(conn)
        _upsert_auction(conn, "A1-ONE", "https://example.com/a/1", "Auction 1", None)
        _upsert_auction(conn, "A1-TWO", "https://example.com/a/2", "Auction 2", None)
        conn.commit()

    calls = []

    async def fake_run_sync(self, **kwargs):
        calls.append((kwargs.get("auction_code"), kwargs.get("auction_url")))
        return SyncRunSummary(
            status="success",
            auction_code=kwargs.get("auction_code"),
            result=DummyResult(),
        )

    monkeypatch.setattr(SyncService, "run_sync", fake_run_sync)

    runner = CliRunner()
    result = runner.invoke(
        sync_multi,
        ["--db", str(db_path), "--include-inactive"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert calls == [
        ("A1-ONE", "https://example.com/a/1"),
        ("A1-TWO", "https://example.com/a/2"),
    ]
    assert "Loading auctions from" in result.output
    assert "Syncing auction A1-ONE" in result.output
    assert "Syncing auction A1-TWO" in result.output

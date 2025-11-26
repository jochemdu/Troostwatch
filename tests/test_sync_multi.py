from click.testing import CliRunner
import importlib

sync_multi_mod = importlib.import_module("troostwatch.interfaces.cli.sync_multi")
from troostwatch.interfaces.cli.sync_multi import sync_multi
from troostwatch.infrastructure.db import ensure_core_schema, ensure_schema, get_connection
from troostwatch.services.sync.sync import _upsert_auction


class DummyResult:
    def __init__(self, code: str):
        self.run_id = 1
        self.status = "success"
        self.pages_scanned = 0
        self.lots_scanned = 0
        self.lots_updated = 0
        self.error_count = 0
        self.errors = []
        self.code = code


def test_sync_multi_uses_db_auctions(monkeypatch, tmp_path):
    db_path = tmp_path / "sync_multi.db"
    with get_connection(db_path) as conn:
        ensure_core_schema(conn)
        ensure_schema(conn)
        _upsert_auction(conn, "A1-ONE", "https://example.com/a/1", "Auction 1", None)
        _upsert_auction(conn, "A1-TWO", "https://example.com/a/2", "Auction 2", None)
        conn.commit()

    calls = []

    def fake_sync_auction_to_db(**kwargs):
        calls.append((kwargs.get("auction_code"), kwargs.get("auction_url")))
        return DummyResult(kwargs.get("auction_code", ""))

    monkeypatch.setattr(sync_multi_mod, "sync_auction_to_db", fake_sync_auction_to_db)

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

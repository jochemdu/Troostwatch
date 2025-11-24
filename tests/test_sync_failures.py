"""Regression tests for sync failure handling and cleanup."""

from pathlib import Path
import sqlite3
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from troostwatch.sync import sync as sync_module
from troostwatch.sync.sync import PageResult, sync_auction_to_db


def test_sync_run_updated_when_processing_raises(monkeypatch, tmp_path):
    """Ensure the sync run record is updated even if lot processing crashes."""

    def fake_collect_pages(*_args, **_kwargs):
        return [PageResult(url="https://example.com/page", html="<html></html>")], [], [], None

    def explode_parse(*_args, **_kwargs):
        raise RuntimeError("boom during lot parsing")

    monkeypatch.setattr(sync_module, "_collect_pages", fake_collect_pages)
    monkeypatch.setattr(sync_module, "parse_auction_page", explode_parse)

    db_path = tmp_path / "sync.db"
    result = sync_auction_to_db(
        str(db_path),
        auction_code="A1-TEST",
        auction_url="https://example.com/a/test",
    )

    assert result.status == "failed"
    assert result.error_count == 1
    assert any("lot parsing" in err for err in result.errors)

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT status, finished_at, error_count FROM sync_runs ORDER BY id DESC LIMIT 1"
        ).fetchone()

    assert row is not None
    status, finished_at, error_count = row
    assert status == "failed"
    assert finished_at is not None
    assert error_count == 1

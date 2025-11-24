import json
import sqlite3
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from troostwatch.sync import sync as sync_module
from troostwatch.sync.sync import PageResult, sync_auction_to_db


def test_sync_records_discovered_pages(monkeypatch, tmp_path):
    base_url = "https://example.com/a/test"
    discovered_pages = [
        base_url,
        f"{base_url}?page=2",
        f"{base_url}?page=3",
    ]

    def fake_collect_pages(*_args, **_kwargs):
        return [PageResult(url=base_url, html="<html><title>Test</title></html>")], [], discovered_pages, None

    monkeypatch.setattr(sync_module, "_collect_pages", fake_collect_pages)
    monkeypatch.setattr(sync_module, "parse_auction_page", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(sync_module, "_iter_lot_card_blocks", lambda *_args, **_kwargs: [])

    db_path = tmp_path / "sync_pages.db"
    result = sync_auction_to_db(
        str(db_path),
        auction_code="A1-TEST",
        auction_url=base_url,
    )

    assert result.status == "success"

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT pagination_pages FROM auctions WHERE auction_code = ?",
            ("A1-TEST",),
        ).fetchone()

    assert row is not None
    stored = json.loads(row[0]) if row[0] is not None else []
    assert stored == discovered_pages

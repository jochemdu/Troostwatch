"""Regression tests for sync failure handling and cleanup."""

from pathlib import Path
import sqlite3
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from troostwatch.services.sync import PageResult, RequestResult, sync_auction_to_db
from troostwatch.infrastructure.web.parsers import LotCardData

# Import the internal sync module for monkeypatching internals.
# This is intentional for test purposes – see scripts/check_imports.py exceptions.
from troostwatch.services.sync import sync as sync_impl_module


def test_sync_stores_lots_even_when_detail_fetch_fails(monkeypatch, tmp_path):
    base_url = "https://example.com/a/test"

    def fake_collect_pages(*_args, **_kwargs):
        return (
            [PageResult(url=base_url, html="<html><title>Test</title></html>")],
            [],
            [base_url],
            None,
        )

    class DummyFetcher:
        def __init__(self, *args, **kwargs):
            pass

        def fetch_sync(self, url):
            return RequestResult(url=url, text="<html></html>", error=None, status=200)

        async def fetch_many(self, urls):
            return [
                RequestResult(url=u, text=None, error="fail", status=500) for u in urls
            ]

    monkeypatch.setattr(sync_impl_module, "_collect_pages", fake_collect_pages)
    monkeypatch.setattr(sync_impl_module, "HttpFetcher", DummyFetcher)
    monkeypatch.setattr(
        sync_impl_module,
        "_wait_and_fetch",
        lambda *args, **kwargs: ("<html></html>", None, time.time()),
    )
    monkeypatch.setattr(
        sync_impl_module,
        "parse_auction_page",
        lambda *_args, **_kwargs: [
            LotCardData(
                auction_code="A1-TEST",
                lot_code="A1-TEST-1",
                title="Lot 1",
                url=f"{base_url}/l/1",
                state="running",
            )
        ],
    )
    monkeypatch.setattr(
        sync_impl_module, "_iter_lot_card_blocks", lambda *_args, **_kwargs: []
    )

    db_path = tmp_path / "sync.db"
    result = sync_auction_to_db(
        str(db_path),
        auction_code="A1-TEST",
        auction_url=base_url,
    )

    assert result.lots_updated == 1

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT a.auction_code, l.lot_code, l.title, l.current_bid_eur, l.detail_hash
            FROM lots l JOIN auctions a ON l.auction_id = a.id
            """
        ).fetchone()

    assert row[0] == "A1-TEST"
    assert row[1] == "A1-TEST-1"
    assert row[2] == "Lot 1"
    # Detail hash should still be populated from the listing-only fallback
    assert row[4] is not None


def test_sync_run_updated_when_processing_raises(monkeypatch, tmp_path):
    """Ensure the sync run record is updated even if lot processing crashes."""

    def fake_collect_pages(*_args, **_kwargs):
        return (
            [PageResult(url="https://example.com/page", html="<html></html>")],
            [],
            [],
            None,
        )

    def explode_parse(*_args, **_kwargs):
        raise RuntimeError("boom during lot parsing")

    monkeypatch.setattr(sync_impl_module, "_collect_pages", fake_collect_pages)
    monkeypatch.setattr(sync_impl_module, "parse_auction_page", explode_parse)

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

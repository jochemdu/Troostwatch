import json
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import the internal sync module for monkeypatching internals.
# This is intentional for test purposes – see scripts/check_imports.py exceptions.
from troostwatch.services.sync import RequestResult  # noqa: E402
from troostwatch.services.sync import sync_auction_to_db  # noqa: E402
from troostwatch.services.sync import sync as sync_module  # noqa: E402


def test_verbose_navigation_logging(monkeypatch, tmp_path):
    base_url = "https://example.com/a/test"
    page_html = "<html><title>Test</title></html>"
    log_file = tmp_path / "sync.log"

    class FakeHttpFetcher:
        def __init__(self, *_, **__):
            self.calls = []

        def fetch_sync(self, url: str) -> RequestResult:
            self.calls.append(url)
            return RequestResult(url=url, text=page_html, error=None)

        async def fetch_many(self, urls):
            return [RequestResult(url=u, text=page_html, error=None) for u in urls]

    monkeypatch.setattr(sync_module, "HttpFetcher", FakeHttpFetcher)
    monkeypatch.setattr(
        sync_module,
        "extract_page_urls",
        lambda *_args, **_kwargs: [base_url, f"{base_url}?page=2"],
    )
    monkeypatch.setattr(sync_module, "parse_auction_page", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        sync_module, "_iter_lot_card_blocks", lambda *_args, **_kwargs: []
    )

    db_path = tmp_path / "sync_pages.db"
    result = sync_auction_to_db(
        str(db_path),
        auction_code="A1-TEST",
        auction_url=base_url,
        verbose=True,
        log_path=str(log_file),
        delay_seconds=0,
    )

    assert result.status == "success"
    assert log_file.exists()
    contents = log_file.read_text(encoding="utf-8")
    assert "Fetching page 1" in contents
    assert "Fetching page 2" in contents
    assert "Processing page 1/2" in contents

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT pagination_pages FROM auctions WHERE auction_code = ?",
            ("A1-TEST",),
        ).fetchone()

    stored = json.loads(row[0]) if row and row[0] else []
    assert stored == [base_url, f"{base_url}?page=2"]

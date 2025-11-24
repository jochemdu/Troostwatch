from pathlib import Path
import sqlite3
import sys

from click.testing import CliRunner

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import importlib

cli_sync_module = importlib.import_module("troostwatch.cli.sync")
from troostwatch.cli.sync import sync
from troostwatch.db import ensure_schema
from troostwatch.sync.sync import SyncRunResult, _upsert_auction


def _seed_auction(db_path: Path, code: str, url: str):
    with sqlite3.connect(db_path) as conn:
        ensure_schema(conn)
        _upsert_auction(conn, code, url, "Test auction", pagination_pages=None)


def test_sync_cli_prompts_existing_auction(monkeypatch, tmp_path):
    db_path = tmp_path / "sync-select.db"
    _seed_auction(db_path, "A1-EXIST", "https://example.com/a/exist")

    captured = {}

    def fake_sync(**kwargs):
        captured.update(kwargs)
        return SyncRunResult(
            run_id=1,
            status="success",
            pages_scanned=0,
            lots_scanned=0,
            lots_updated=0,
            error_count=0,
            errors=[],
        )

    monkeypatch.setattr(cli_sync_module, "sync_auction_to_db", fake_sync)

    runner = CliRunner()
    result = runner.invoke(sync, ["--db", str(db_path)], input="1\n")

    assert result.exit_code == 0, result.output
    assert captured.get("auction_code") == "A1-EXIST"
    assert captured.get("auction_url") == "https://example.com/a/exist"


def test_sync_cli_uses_existing_url_when_code_given(monkeypatch, tmp_path):
    db_path = tmp_path / "sync-select-url.db"
    _seed_auction(db_path, "A1-EXIST", "https://example.com/a/exist")

    captured = {}

    def fake_sync(**kwargs):
        captured.update(kwargs)
        return SyncRunResult(
            run_id=2,
            status="success",
            pages_scanned=0,
            lots_scanned=0,
            lots_updated=0,
            error_count=0,
            errors=[],
        )

    monkeypatch.setattr(cli_sync_module, "sync_auction_to_db", fake_sync)

    runner = CliRunner()
    result = runner.invoke(
        sync,
        ["--db", str(db_path), "--auction-code", "A1-EXIST"],
    )

    assert result.exit_code == 0, result.output
    assert captured.get("auction_code") == "A1-EXIST"
    assert captured.get("auction_url") == "https://example.com/a/exist"

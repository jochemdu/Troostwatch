from pathlib import Path
import sqlite3
import sys
from typing import Any

from click.testing import CliRunner

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import importlib

cli_sync_module = importlib.import_module("troostwatch.interfaces.cli.sync")
from troostwatch.interfaces.cli.context import build_sync_command_context
from troostwatch.interfaces.cli.sync import sync
from troostwatch.services.sync_service import AuctionSelection, SyncRunSummary
from troostwatch.services.sync import SyncRunResult, _upsert_auction


def _seed_auction(db_path: Path, code: str, url: str):
    with sqlite3.connect(db_path) as conn:
        from troostwatch.infrastructure.db import ensure_schema

        ensure_schema(conn)
        _upsert_auction(conn, code, url, "Test auction", pagination_pages=None)


class FakeSyncService:
    def __init__(self, *, available: list[dict[str, Any]], auto_resolve: bool = True):
        self.available = available
        self.auto_resolve = auto_resolve
        self.run_kwargs: dict[str, Any] = {}

    def choose_auction(self, auction_code: str | None, auction_url: str | None):
        resolved_code = auction_code
        if resolved_code is None and self.auto_resolve and self.available:
            resolved_code = self.available[0]["auction_code"]
        resolved_url = auction_url
        if resolved_code and not resolved_url:
            match = next((a for a in self.available if a.get("auction_code") == resolved_code), None)
            resolved_url = match.get("url") if match else None
        return AuctionSelection(
            resolved_code=resolved_code,
            resolved_url=resolved_url,
            available=self.available,
            preferred_index=0 if self.available else None,
        )

    async def run_sync(self, **kwargs):
        self.run_kwargs = kwargs
        return SyncRunSummary(
            status="success",
            result=SyncRunResult(
                run_id=1,
                status="success",
                pages_scanned=0,
                lots_scanned=0,
                lots_updated=0,
                error_count=0,
                errors=[],
            ),
        )


def _mock_service(monkeypatch, available: list[dict[str, Any]], *, auto_resolve: bool = True):
    fake_service = FakeSyncService(available=available, auto_resolve=auto_resolve)

    def _factory(*args, **kwargs):
        return fake_service

    monkeypatch.setattr(cli_sync_module, "SyncService", _factory)
    return fake_service


def test_sync_cli_prompts_existing_auction(monkeypatch, tmp_path):
    db_path = tmp_path / "sync-select.db"
    _seed_auction(db_path, "A1-EXIST", "https://example.com/a/exist")

    service = _mock_service(
        monkeypatch,
        [
            {
                "auction_code": "A1-EXIST",
                "url": "https://example.com/a/exist",
                "title": "Test auction",
            }
        ],
        auto_resolve=False,
    )
    monkeypatch.setattr(
        cli_sync_module,
        "build_sync_command_context",
        lambda **kwargs: build_sync_command_context(**kwargs),
    )

    runner = CliRunner()
    result = runner.invoke(sync, ["--db", str(db_path)], input="1\n")

    assert result.exit_code == 0, result.output
    assert service.run_kwargs.get("auction_code") == "A1-EXIST"
    assert service.run_kwargs.get("auction_url") == "https://example.com/a/exist"
    assert "Select an auction to sync:" in result.output


def test_sync_cli_uses_existing_url_when_code_given(monkeypatch, tmp_path):
    db_path = tmp_path / "sync-select-url.db"
    _seed_auction(db_path, "A1-EXIST", "https://example.com/a/exist")

    service = _mock_service(
        monkeypatch,
        [
            {
                "auction_code": "A1-EXIST",
                "url": "https://example.com/a/exist",
                "title": "Test auction",
            }
        ],
    )
    monkeypatch.setattr(
        cli_sync_module,
        "build_sync_command_context",
        lambda **kwargs: build_sync_command_context(**kwargs),
    )

    runner = CliRunner()
    result = runner.invoke(
        sync,
        ["--db", str(db_path), "--auction-code", "A1-EXIST"],
    )

    assert result.exit_code == 0, result.output
    assert service.run_kwargs.get("auction_code") == "A1-EXIST"
    assert service.run_kwargs.get("auction_url") == "https://example.com/a/exist"


def test_sync_cli_defaults_preferred_auction(monkeypatch, tmp_path):
    db_path = tmp_path / "sync-preferred.db"
    _seed_auction(db_path, "A1-ONE", "https://example.com/a/one")
    _seed_auction(db_path, "A1-TWO", "https://example.com/a/two")

    class PreferredService(FakeSyncService):
        def choose_auction(self, auction_code: str | None, auction_url: str | None):
            return AuctionSelection(
                resolved_code=None,
                resolved_url=None,
                available=self.available,
                preferred_index=1,
            )

    service = PreferredService(
        available=[
            {"auction_code": "A1-ONE", "url": "https://example.com/a/one", "title": "Auction 1"},
            {"auction_code": "A1-TWO", "url": "https://example.com/a/two", "title": "Auction 2"},
        ]
    )

    monkeypatch.setattr(cli_sync_module, "SyncService", lambda *args, **kwargs: service)
    monkeypatch.setattr(
        cli_sync_module,
        "build_sync_command_context",
        lambda **kwargs: build_sync_command_context(**kwargs),
    )

    runner = CliRunner()
    # Accept the default (preferred) auction by pressing Enter.
    result = runner.invoke(sync, ["--db", str(db_path)], input="\n")

    assert result.exit_code == 0, result.output
    assert service.run_kwargs.get("auction_code") == "A1-TWO"
    assert service.run_kwargs.get("auction_url") == "https://example.com/a/two"
    # The prompt should display the default choice number (2 in this case).
    assert "Standaard keuze: 2" in result.output


def test_sync_cli_reports_dry_run(monkeypatch, tmp_path):
    db_path = tmp_path / "sync-dry-run.db"
    _seed_auction(db_path, "A1-EXIST", "https://example.com/a/exist")

    service = _mock_service(
        monkeypatch,
        [
            {
                "auction_code": "A1-EXIST",
                "url": "https://example.com/a/exist",
                "title": "Test auction",
            }
        ],
    )
    monkeypatch.setattr(
        cli_sync_module,
        "build_sync_command_context",
        lambda **kwargs: build_sync_command_context(**kwargs),
    )

    runner = CliRunner()
    result = runner.invoke(sync, ["--db", str(db_path), "--dry-run", "--auction-code", "A1-EXIST"])

    assert result.exit_code == 0, result.output
    assert service.run_kwargs.get("dry_run") is True
    assert "Dry-run enabled" in result.output


def test_sync_cli_handles_service_error(monkeypatch, tmp_path):
    db_path = tmp_path / "sync-error.db"
    _seed_auction(db_path, "A1-EXIST", "https://example.com/a/exist")

    class ErrorService(FakeSyncService):
        async def run_sync(self, **kwargs):
            return SyncRunSummary(status="error", result=None, error="boom")

    service = ErrorService(available=[{"auction_code": "A1-EXIST", "url": "https://example.com/a/exist"}])
    monkeypatch.setattr(cli_sync_module, "SyncService", lambda *args, **kwargs: service)
    monkeypatch.setattr(
        cli_sync_module,
        "build_sync_command_context",
        lambda **kwargs: build_sync_command_context(**kwargs),
    )

    runner = CliRunner()
    result = runner.invoke(sync, ["--db", str(db_path), "--auction-code", "A1-EXIST"])

    assert result.exit_code == 0
    assert "Error during sync: boom" in result.output

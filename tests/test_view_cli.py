from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from click.testing import CliRunner

from troostwatch.infrastructure.db import ensure_schema
from troostwatch.infrastructure.db.repositories import LotRepository
from troostwatch.interfaces.cli.view import view


def _seed_db(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    try:
        ensure_schema(conn)
        conn.execute(
            "INSERT INTO auctions (auction_code, title, url) VALUES (?, ?, ?)",
            ("A1-111", "Test Auction", "http://example.com"),
        )
        auction_id = conn.execute(
            "SELECT id FROM auctions WHERE auction_code = ?", ("A1-111",)
        ).fetchone()[0]
        conn.execute(
            """
            INSERT INTO lots (
                auction_id, lot_code, title, state, current_bid_eur, bid_count,
                current_bidder_label, closing_time_current
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                auction_id,
                "0001",
                "Open lot",
                "open",
                100.0,
                2,
                "B-10",
                "2025-01-01T10:00:00Z",
            ),
        )
        conn.execute(
            """
            INSERT INTO lots (
                auction_id, lot_code, title, state, current_bid_eur, bid_count,
                current_bidder_label, closing_time_current
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                auction_id,
                "0002",
                "Closed lot",
                "closed",
                250.0,
                4,
                "B-11",
                "2024-12-31T15:00:00Z",
            ),
        )
        conn.commit()
    finally:
        conn.close()


def test_list_lots_filters(tmp_path: Path) -> None:
    db_file = tmp_path / "lots.db"
    _seed_db(db_file)

    conn = sqlite3.connect(db_file)
    try:
        lot_repo = LotRepository(conn)
        all_lots = lot_repo.list_lots()
        assert len(all_lots) == 2

        open_lots = lot_repo.list_lots(state="open")
        assert [lot["lot_code"] for lot in open_lots] == ["0001"]

        limited = lot_repo.list_lots(limit=1)
        assert len(limited) == 1
    finally:
        conn.close()


def test_view_cli_text_output(tmp_path: Path) -> None:
    db_file = tmp_path / "lots.db"
    _seed_db(db_file)

    runner = CliRunner()
    result = runner.invoke(
        view, ["--db", str(db_file), "--auction-code", "A1-111", "--limit", "1"]
    )

    assert result.exit_code == 0
    assert "Showing 1 lot(s):" in result.output
    assert "[A1-111/0001]" in result.output


def test_view_cli_json_output(tmp_path: Path) -> None:
    db_file = tmp_path / "lots.db"
    _seed_db(db_file)

    runner = CliRunner()
    result = runner.invoke(
        view,
        [
            "--db",
            str(db_file),
            "--auction-code",
            "A1-111",
            "--state",
            "open",
            "--limit",
            "0",
            "--json-output",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert isinstance(payload, list)
    assert len(payload) == 1
    assert payload[0]["lot_code"] == "0001"


def test_view_cli_json_output_no_limit(tmp_path: Path) -> None:
    db_file = tmp_path / "lots.db"
    _seed_db(db_file)

    runner = CliRunner()
    result = runner.invoke(
        view, ["--db", str(db_file), "--limit", "0", "--json-output"]
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert isinstance(payload, list)
    assert len(payload) == 2

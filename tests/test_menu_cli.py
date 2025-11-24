from __future__ import annotations

import sqlite3
from pathlib import Path

from click.testing import CliRunner

from troostwatch.cli.menu import menu
from troostwatch.db import ensure_schema


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
        conn.commit()
    finally:
        conn.close()


def test_menu_lists_choices_and_exit() -> None:
    runner = CliRunner()
    result = runner.invoke(menu, input="exit\n")

    assert result.exit_code == 0
    assert "sync" in result.output
    assert "view" in result.output
    assert "Goodbye" in result.output


def test_menu_view_flow(tmp_path: Path) -> None:
    db_file = tmp_path / "lots.db"
    _seed_db(db_file)

    runner = CliRunner()
    user_input = "\n".join(
        [
            "view",
            str(db_file),
            "A1-111",
            "",  # state filter blank
            "1",  # limit
            "n",  # JSON output
            "exit",
            "",
        ]
    )
    result = runner.invoke(menu, input=user_input)

    assert result.exit_code == 0
    assert "Showing 1 lot(s):" in result.output
    assert "[A1-111/0001]" in result.output

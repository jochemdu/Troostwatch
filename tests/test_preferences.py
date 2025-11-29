from __future__ import annotations

import sqlite3
from pathlib import Path

from troostwatch.infrastructure.db import ensure_schema
from troostwatch.infrastructure.db.repositories import PreferenceRepository, AuctionRepository


def _seed_auctions(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO auctions (auction_code, title, url) VALUES (?, ?, ?)",
        ("A1-OPEN", "Open Auction", "http://example.com/open"),
    )
    conn.execute(
        "INSERT INTO auctions (auction_code, title, url) VALUES (?, ?, ?)",
        ("A1-CLOSED", "Closed Auction", "http://example.com/closed"),
    )
    open_id = conn.execute(
        "SELECT id FROM auctions WHERE auction_code = ?", ("A1-OPEN",)
    ).fetchone()[0]
    closed_id = conn.execute(
        "SELECT id FROM auctions WHERE auction_code = ?", ("A1-CLOSED",)
    ).fetchone()[0]
    conn.execute(
        "INSERT INTO lots (auction_id, lot_code, state, title) VALUES (?, ?, ?, ?)",
        (open_id, "A1-OPEN-1", "open", "Lot"),
    )
    conn.execute(
        "INSERT INTO lots (auction_id, lot_code, state, title) VALUES (?, ?, ?, ?)",
        (closed_id, "A1-CLOSED-1", "closed", "Closed Lot"),
    )
    conn.commit()


def test_preferences_round_trip(tmp_path: Path) -> None:
    db_path = tmp_path / "prefs.db"
    conn = sqlite3.connect(db_path)
    try:
        ensure_schema(conn)
        pref_repo = PreferenceRepository(conn)
        assert pref_repo.get("preferred_auction") is None
        pref_repo.set("preferred_auction", "A1-OPEN")
        assert pref_repo.get("preferred_auction") == "A1-OPEN"
        pref_repo.set("preferred_auction", None)
        assert pref_repo.get("preferred_auction") is None
    finally:
        conn.close()


def test_list_auctions_active_filter(tmp_path: Path) -> None:
    db_path = tmp_path / "auctions.db"
    conn = sqlite3.connect(db_path)
    try:
        ensure_schema(conn)
        _seed_auctions(conn)
        auction_repo = AuctionRepository(conn)
        active = auction_repo.list(only_active=True)
        assert [a["auction_code"] for a in active] == ["A1-OPEN"]
        all_auctions = auction_repo.list(only_active=False)
        assert len(all_auctions) == 2
    finally:
        conn.close()

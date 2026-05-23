from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from troostwatch.infrastructure.db import ensure_schema
from troostwatch.infrastructure.db.repositories import BidRepository
from troostwatch.services.bidding import BidError, BiddingService


class DummyClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def post_json(self, url: str, payload: dict) -> dict:
        self.calls.append((url, payload))
        return {"status": "ok"}


def _create_auction(conn: sqlite3.Connection, auction_code: str) -> int:
    cur = conn.execute(
        "INSERT INTO auctions (auction_code, title, url) VALUES (?, ?, ?)",
        (auction_code, "Auction", "http://example.com"),
    )
    return int(cur.lastrowid)


def test_record_bid_missing_buyer_raises(tmp_path: Path) -> None:
    db_path = tmp_path / "bids.db"
    conn = sqlite3.connect(db_path)
    try:
        ensure_schema(conn)
        auction_id = _create_auction(conn, "A1")
        conn.execute(
            "INSERT INTO lots (auction_id, lot_code) VALUES (?, ?)",
            (auction_id, "A1-1"),
        )
        conn.commit()

        repo = BidRepository(conn)
        with pytest.raises(ValueError, match="Buyer 'missing' does not exist"):
            repo.record_bid("missing", "A1", "A1-1", 10.0, None)
    finally:
        conn.close()


def test_record_bid_missing_lot_raises(tmp_path: Path) -> None:
    db_path = tmp_path / "bids.db"
    conn = sqlite3.connect(db_path)
    try:
        ensure_schema(conn)
        _create_auction(conn, "A1")
        conn.execute(
            "INSERT INTO buyers (label, name) VALUES (?, ?)", ("buyer-1", "Buyer 1")
        )
        conn.commit()

        repo = BidRepository(conn)
        with pytest.raises(
            ValueError, match="Lot 'A1-2' in auction 'A1' does not exist"
        ):
            repo.record_bid("buyer-1", "A1", "A1-2", 10.0, None)
    finally:
        conn.close()


def test_submit_bid_surfaces_persistence_failure(tmp_path: Path) -> None:
    db_path = tmp_path / "persist.db"
    conn = sqlite3.connect(db_path)
    try:
        ensure_schema(conn)
        auction_id = _create_auction(conn, "A1")
        conn.execute(
            "INSERT INTO lots (auction_id, lot_code) VALUES (?, ?)",
            (auction_id, "A1-1"),
        )
        conn.commit()
    finally:
        conn.close()

    client = DummyClient()
    service = BiddingService.from_sqlite_path(
        client, str(db_path), api_base_url="http://example.com/api"
    )

    with pytest.raises(
        BidError, match="Failed to persist bid locally: Buyer 'missing' does not exist"
    ):
        service.submit_bid(
            buyer_label="missing",
            auction_code="A1",
            lot_code="A1-1",
            amount_eur=25.0,
            note=None,
        )

    assert len(client.calls) == 1

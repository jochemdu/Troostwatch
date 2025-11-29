from __future__ import annotations

import sqlite3

from ..connection import iso_utcnow
from .base import BaseRepository
from .buyers import BuyerRepository
from .lots import LotRepository


class BidRepository(BaseRepository):
    def __init__(
        self,
        conn: sqlite3.Connection,
        buyers: BuyerRepository | None = None,
        lots: LotRepository | None = None,
    ) -> None:
        super().__init__(conn)
        self.buyers = buyers or BuyerRepository(conn)
        self.lots = lots or LotRepository(conn)

    def record_bid(
        self,
        buyer_label: str,
        auction_code: str,
        lot_code: str,
        amount_eur: float,
        note: str | None = None,
    ) -> None:
        buyer_id = self.buyers.get_id(buyer_label)
        lot_id = self.lots.get_id(lot_code, auction_code)
        if buyer_id is None:
            raise ValueError(f"Buyer '{buyer_label}' does not exist")
        if lot_id is None:
            raise ValueError(
                f"Lot '{lot_code}' in auction '{auction_code}' does not exist"
            )
        self._execute(
            """
            INSERT INTO my_bids (lot_id, buyer_id, amount_eur, placed_at, note)
            VALUES (?, ?, ?, ?, ?)
            """,
            (lot_id, buyer_id, amount_eur, iso_utcnow(), note),
        )
        self.conn.commit()

    def list(
        self,
        buyer_label: str | None = None,
        lot_code: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, object]]:
        """List bids with optional filters."""
        query = """
            SELECT
                mb.id,
                b.label AS buyer_label,
                l.lot_code,
                a.auction_code,
                l.title AS lot_title,
                mb.amount_eur,
                mb.placed_at,
                mb.note
            FROM my_bids mb
            JOIN buyers b ON mb.buyer_id = b.id
            JOIN lots l ON mb.lot_id = l.id
            JOIN auctions a ON l.auction_id = a.id
            WHERE 1=1
        """
        params: list[object] = []

        if buyer_label:
            query += " AND b.label = ?"
            params.append(buyer_label)
        if lot_code:
            query += " AND l.lot_code = ?"
            params.append(lot_code)

        query += " ORDER BY mb.placed_at DESC LIMIT ?"
        params.append(limit)

        return self._fetch_all_as_dicts(query, tuple(params))

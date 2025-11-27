from __future__ import annotations

from typing import Dict, List, Optional

from ..connection import iso_utcnow
from .buyers import BuyerRepository
from .lots import LotRepository


class BidRepository:
    def __init__(self, conn, buyers: BuyerRepository | None = None, lots: LotRepository | None = None) -> None:
        self.conn = conn
        self.buyers = buyers or BuyerRepository(conn)
        self.lots = lots or LotRepository(conn)

    def record_bid(
        self,
        buyer_label: str,
        auction_code: str,
        lot_code: str,
        amount_eur: float,
        note: Optional[str] = None,
    ) -> None:
        buyer_id = self.buyers.get_id(buyer_label)
        lot_id = self.lots.get_id(lot_code, auction_code)
        if buyer_id is None:
            raise ValueError(f"Buyer '{buyer_label}' does not exist")
        if lot_id is None:
            raise ValueError(
                f"Lot '{lot_code}' in auction '{auction_code}' does not exist"
            )
        self.conn.execute(
            """
            INSERT INTO my_bids (lot_id, buyer_id, amount_eur, placed_at, note)
            VALUES (?, ?, ?, ?, ?)
            """,
            (lot_id, buyer_id, amount_eur, iso_utcnow(), note),
        )
        self.conn.commit()

    def list(
        self,
        buyer_label: Optional[str] = None,
        lot_code: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, object]]:
        """List bids with optional filters."""
        query = """
            SELECT
                mb.id,
                b.label AS buyer_label,
                l.lot_code,
                l.auction_code,
                l.title AS lot_title,
                mb.amount_eur,
                mb.placed_at,
                mb.note
            FROM my_bids mb
            JOIN buyers b ON mb.buyer_id = b.id
            JOIN lots l ON mb.lot_id = l.id
            WHERE 1=1
        """
        params: List[object] = []
        
        if buyer_label:
            query += " AND b.label = ?"
            params.append(buyer_label)
        if lot_code:
            query += " AND l.lot_code = ?"
            params.append(lot_code)
        
        query += " ORDER BY mb.placed_at DESC LIMIT ?"
        params.append(limit)
        
        cursor = self.conn.execute(query, params)
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

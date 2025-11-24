from __future__ import annotations

from typing import Dict, List, Optional

from .buyers import BuyerRepository
from .lots import LotRepository


class PositionRepository:
    def __init__(self, conn, buyers: BuyerRepository | None = None, lots: LotRepository | None = None) -> None:
        self.conn = conn
        self.buyers = buyers or BuyerRepository(conn)
        self.lots = lots or LotRepository(conn)

    def upsert(
        self,
        buyer_label: str,
        lot_code: str,
        auction_code: Optional[str] = None,
        *,
        track_active: bool = True,
        max_budget_total_eur: Optional[float] = None,
        my_highest_bid_eur: Optional[float] = None,
    ) -> None:
        buyer_id = self.buyers.get_id(buyer_label)
        if buyer_id is None:
            raise ValueError(f"Buyer with label '{buyer_label}' does not exist")
        lot_id = self.lots.get_id(lot_code, auction_code)
        if lot_id is None:
            raise ValueError(f"Lot with code '{lot_code}' not found (auction: {auction_code})")
        self.conn.execute(
            """
            INSERT INTO my_lot_positions (buyer_id, lot_id, track_active, max_budget_total_eur, my_highest_bid_eur)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(buyer_id, lot_id) DO UPDATE SET
                track_active = excluded.track_active,
                max_budget_total_eur = excluded.max_budget_total_eur,
                my_highest_bid_eur = excluded.my_highest_bid_eur
            """,
            (buyer_id, lot_id, 1 if track_active else 0, max_budget_total_eur, my_highest_bid_eur),
        )
        self.conn.commit()

    def list(self, buyer_label: Optional[str] = None) -> List[Dict[str, Optional[str]]]:
        params: List = []
        query = """
            SELECT b.label AS buyer_label,
                   a.auction_code AS auction_code,
                   l.lot_code AS lot_code,
                   p.track_active,
                   p.max_budget_total_eur,
                   p.my_highest_bid_eur,
                   l.title AS lot_title,
                   l.state AS lot_state,
                   l.current_bid_eur
            FROM my_lot_positions p
            JOIN buyers b ON p.buyer_id = b.id
            JOIN lots l ON p.lot_id = l.id
            JOIN auctions a ON l.auction_id = a.id
        """
        if buyer_label:
            query += " WHERE b.label = ?"
            params.append(buyer_label)
        query += " ORDER BY a.auction_code, l.lot_code"
        cur = self.conn.execute(query, tuple(params))
        columns = [c[0] for c in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]

    def delete(self, buyer_label: str, lot_code: str, auction_code: Optional[str] = None) -> None:
        buyer_id = self.buyers.get_id(buyer_label)
        if buyer_id is None:
            raise ValueError(f"Buyer with label '{buyer_label}' does not exist")
        lot_id = self.lots.get_id(lot_code, auction_code)
        if lot_id is None:
            raise ValueError(f"Lot with code '{lot_code}' not found (auction: {auction_code})")
        self.conn.execute(
            "DELETE FROM my_lot_positions WHERE buyer_id = ? AND lot_id = ?",
            (buyer_id, lot_id),
        )
        self.conn.commit()

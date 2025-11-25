from __future__ import annotations

from typing import Optional

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

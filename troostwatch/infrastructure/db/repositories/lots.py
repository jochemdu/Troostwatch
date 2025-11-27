from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional

from ..schema import ensure_schema
from troostwatch.infrastructure.web.parsers.lot_card import LotCardData
from troostwatch.infrastructure.web.parsers.lot_detail import LotDetailData


class LotRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        ensure_schema(self.conn)

    def get_id(self, lot_code: str, auction_code: Optional[str] = None) -> Optional[int]:
        query = "SELECT l.id FROM lots l JOIN auctions a ON l.auction_id = a.id WHERE l.lot_code = ?"

        def _lookup(code: str) -> Optional[int]:
            params: List = [code]
            local_query = query
            if auction_code is not None:
                local_query += " AND a.auction_code = ?"
                params.append(auction_code)
            cur = self.conn.execute(local_query, tuple(params))
            row = cur.fetchone()
            return row[0] if row else None

        lot_id = _lookup(lot_code)
        if lot_id is None and auction_code and not lot_code.startswith(f"{auction_code}-"):
            lot_id = _lookup(f"{auction_code}-{lot_code}")
        return lot_id

    def list_lot_codes_by_auction(self, auction_code: str) -> List[str]:
        rows = self.conn.execute(
            """
            SELECT l.lot_code
            FROM lots l
            JOIN auctions a ON l.auction_id = a.id
            WHERE a.auction_code = ?
            ORDER BY l.lot_code
            """,
            (auction_code,),
        ).fetchall()
        return [r[0] for r in rows]

    def list_lots(
        self,
        *,
        auction_code: Optional[str] = None,
        state: Optional[str] = None,
        brand: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Optional[str]]]:
        query = """
            SELECT a.auction_code AS auction_code,
                   l.lot_code AS lot_code,
                   l.title AS title,
                   l.state AS state,
                   l.current_bid_eur AS current_bid_eur,
                   l.bid_count AS bid_count,
                   l.current_bidder_label AS current_bidder_label,
                   l.closing_time_current AS closing_time_current,
                   l.closing_time_original AS closing_time_original,
                   l.brand AS brand
            FROM lots l
            JOIN auctions a ON l.auction_id = a.id
        """

        conditions: list[str] = []
        params: list = []
        if auction_code:
            conditions.append("a.auction_code = ?")
            params.append(auction_code)
        if state:
            conditions.append("l.state = ?")
            params.append(state)
        if brand:
            conditions.append("l.brand = ?")
            params.append(brand)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY a.auction_code, l.lot_code"
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        cur = self.conn.execute(query, tuple(params))
        columns = [c[0] for c in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]

    def get_lot_detail(self, lot_code: str, auction_code: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get detailed lot information."""
        query = """
            SELECT a.auction_code, l.lot_code, l.title, l.url, l.state,
                   l.current_bid_eur, l.bid_count, l.opening_bid_eur,
                   l.closing_time_current, l.closing_time_original, l.brand,
                   l.location_city, l.location_country, l.notes
            FROM lots l
            JOIN auctions a ON l.auction_id = a.id
            WHERE l.lot_code = ?
        """
        params: List = [lot_code]
        if auction_code:
            query += " AND a.auction_code = ?"
            params.append(auction_code)
        
        cur = self.conn.execute(query, tuple(params))
        row = cur.fetchone()
        if not row:
            return None
        
        columns = [c[0] for c in cur.description]
        return dict(zip(columns, row))

    def get_lot_specs(self, lot_code: str, auction_code: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get specifications (product_layers) for a lot."""
        lot_id = self.get_id(lot_code, auction_code)
        if not lot_id:
            return []
        
        cur = self.conn.execute(
            "SELECT id, title AS key, value FROM product_layers WHERE lot_id = ? ORDER BY layer",
            (lot_id,)
        )
        columns = [c[0] for c in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]

    def get_reference_prices(self, lot_code: str, auction_code: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all reference prices for a lot."""
        lot_id = self.get_id(lot_code, auction_code)
        if not lot_id:
            return []
        
        cur = self.conn.execute(
            """SELECT id, condition, price_eur, source, url, notes, created_at
               FROM reference_prices WHERE lot_id = ? ORDER BY created_at DESC""",
            (lot_id,)
        )
        columns = [c[0] for c in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]

    def add_reference_price(
        self,
        lot_code: str,
        price_eur: float,
        condition: str = "used",
        source: Optional[str] = None,
        url: Optional[str] = None,
        notes: Optional[str] = None,
        auction_code: Optional[str] = None,
    ) -> int:
        """Add a reference price for a lot. Returns the new id."""
        lot_id = self.get_id(lot_code, auction_code)
        if not lot_id:
            raise ValueError(f"Lot '{lot_code}' not found")
        
        cur = self.conn.execute(
            """INSERT INTO reference_prices (lot_id, condition, price_eur, source, url, notes)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (lot_id, condition, price_eur, source, url, notes)
        )
        self.conn.commit()
        return cur.lastrowid or 0

    def update_reference_price(
        self,
        ref_id: int,
        price_eur: Optional[float] = None,
        condition: Optional[str] = None,
        source: Optional[str] = None,
        url: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> bool:
        """Update a reference price. Returns True if updated."""
        updates = []
        params: List = []
        
        if price_eur is not None:
            updates.append("price_eur = ?")
            params.append(price_eur)
        if condition is not None:
            updates.append("condition = ?")
            params.append(condition)
        if source is not None:
            updates.append("source = ?")
            params.append(source)
        if url is not None:
            updates.append("url = ?")
            params.append(url)
        if notes is not None:
            updates.append("notes = ?")
            params.append(notes)
        
        if not updates:
            return True
        
        updates.append("updated_at = datetime('now')")
        params.append(ref_id)
        
        cur = self.conn.execute(
            f"UPDATE reference_prices SET {', '.join(updates)} WHERE id = ?",
            tuple(params),
        )
        self.conn.commit()
        return cur.rowcount > 0

    def delete_reference_price(self, ref_id: int) -> bool:
        """Delete a reference price. Returns True if deleted."""
        cur = self.conn.execute("DELETE FROM reference_prices WHERE id = ?", (ref_id,))
        self.conn.commit()
        return cur.rowcount > 0

    def update_lot(
        self,
        lot_code: str,
        auction_code: Optional[str] = None,
        *,
        notes: Optional[str] = None,
    ) -> bool:
        """Update user-editable lot fields (notes). Returns True if a row was updated."""
        lot_id = self.get_id(lot_code, auction_code)
        if not lot_id:
            return False
        
        if notes is not None:
            self.conn.execute(
                "UPDATE lots SET notes = ? WHERE id = ?",
                (notes, lot_id),
            )
            self.conn.commit()
        return True

    def upsert_lot_spec(self, lot_code: str, key: str, value: str, auction_code: Optional[str] = None) -> int:
        """Add or update a specification for a lot. Returns the spec id."""
        lot_id = self.get_id(lot_code, auction_code)
        if not lot_id:
            raise ValueError(f"Lot '{lot_code}' not found")
        
        # Check if spec exists
        cur = self.conn.execute(
            "SELECT id FROM product_layers WHERE lot_id = ? AND title = ?",
            (lot_id, key)
        )
        existing = cur.fetchone()
        
        if existing:
            self.conn.execute(
                "UPDATE product_layers SET value = ? WHERE id = ?",
                (value, existing[0])
            )
            self.conn.commit()
            return existing[0]
        else:
            # Get max layer number
            cur = self.conn.execute(
                "SELECT COALESCE(MAX(layer), -1) + 1 FROM product_layers WHERE lot_id = ?",
                (lot_id,)
            )
            next_layer = cur.fetchone()[0]
            
            cur = self.conn.execute(
                "INSERT INTO product_layers (lot_id, layer, title, value) VALUES (?, ?, ?, ?)",
                (lot_id, next_layer, key, value)
            )
            self.conn.commit()
            return cur.lastrowid or 0

    def delete_lot_spec(self, spec_id: int) -> bool:
        """Delete a specification by id. Returns True if deleted."""
        cur = self.conn.execute("DELETE FROM product_layers WHERE id = ?", (spec_id,))
        self.conn.commit()
        return cur.rowcount > 0

    def upsert_from_parsed(
        self,
        auction_id: int,
        card: LotCardData,
        detail: LotDetailData,
        *,
        listing_hash: str,
        detail_hash: str,
        last_seen_at: str,
        detail_last_seen_at: str,
    ) -> None:
        lot_title = detail.title or card.title
        lot_url = detail.url or card.url
        lot_state = detail.state or card.state
        lot_opens_at = detail.opens_at or card.opens_at
        lot_closing_current = detail.closing_time_current or card.closing_time_current
        lot_closing_original = detail.closing_time_original
        lot_bid_count = detail.bid_count if detail.bid_count is not None else card.bid_count
        lot_opening_bid = _choose_value(detail.opening_bid_eur, card.price_eur if card.is_price_opening_bid else None)
        lot_current_bid = _choose_value(detail.current_bid_eur, card.price_eur)
        location_city = detail.location_city or card.location_city
        location_country = detail.location_country or card.location_country

        self.conn.execute(
            """
            INSERT INTO lots (
                auction_id, lot_code, title, url, state, status, opens_at,
                closing_time_current, closing_time_original, bid_count,
                opening_bid_eur, current_bid_eur, current_bidder_label,
                buyer_fee_percent, buyer_fee_vat_percent, vat_percent,
                awarding_state, total_example_price_eur, location_city,
                location_country, seller_allocation_note, brand,
                listing_hash, detail_hash, last_seen_at, detail_last_seen_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(auction_id, lot_code) DO UPDATE SET
                title = excluded.title,
                url = excluded.url,
                state = excluded.state,
                status = excluded.status,
                opens_at = excluded.opens_at,
                closing_time_current = excluded.closing_time_current,
                closing_time_original = excluded.closing_time_original,
                bid_count = excluded.bid_count,
                opening_bid_eur = excluded.opening_bid_eur,
                current_bid_eur = excluded.current_bid_eur,
                current_bidder_label = excluded.current_bidder_label,
                buyer_fee_percent = excluded.buyer_fee_percent,
                buyer_fee_vat_percent = excluded.buyer_fee_vat_percent,
                vat_percent = excluded.vat_percent,
                awarding_state = excluded.awarding_state,
                total_example_price_eur = excluded.total_example_price_eur,
                location_city = excluded.location_city,
                location_country = excluded.location_country,
                seller_allocation_note = excluded.seller_allocation_note,
                brand = excluded.brand,
                listing_hash = excluded.listing_hash,
                detail_hash = excluded.detail_hash,
                last_seen_at = excluded.last_seen_at,
                detail_last_seen_at = excluded.detail_last_seen_at
            """,
            (
                auction_id,
                card.lot_code,
                lot_title,
                lot_url,
                lot_state,
                lot_state,
                lot_opens_at,
                lot_closing_current,
                lot_closing_original,
                lot_bid_count,
                lot_opening_bid,
                lot_current_bid,
                detail.current_bidder_label,
                detail.auction_fee_pct,
                detail.auction_fee_vat_pct,
                detail.vat_on_bid_pct,
                detail.state,
                detail.total_example_price_eur,
                location_city,
                location_country,
                detail.seller_allocation_note,
                detail.brand,
                listing_hash,
                detail_hash,
                last_seen_at,
                detail_last_seen_at,
            ),
        )

        # Upsert bid history if available
        if detail.bid_history:
            self._upsert_bid_history(card.lot_code, auction_id, detail.bid_history)

    def _upsert_bid_history(
        self,
        lot_code: str,
        auction_id: int,
        bid_history: list,
    ) -> None:
        """Insert or update bid history entries for a lot."""
        from troostwatch.infrastructure.web.parsers.lot_detail import BidHistoryEntry

        # Get lot_id
        cur = self.conn.execute(
            "SELECT id FROM lots WHERE lot_code = ? AND auction_id = ?",
            (lot_code, auction_id),
        )
        row = cur.fetchone()
        if not row:
            return
        lot_id = row[0]

        # Clear existing bid history for this lot and insert fresh
        self.conn.execute("DELETE FROM bid_history WHERE lot_id = ?", (lot_id,))

        for entry in bid_history:
            if isinstance(entry, BidHistoryEntry):
                self.conn.execute(
                    """
                    INSERT INTO bid_history (lot_id, bidder_label, amount_eur, bid_time)
                    VALUES (?, ?, ?, ?)
                    """,
                    (lot_id, entry.bidder_label, entry.amount_eur, entry.timestamp),
                )


def _choose_value(*values: Optional[str | float | int | bool]):
    for value in values:
        if value is not None:
            return value
    return None

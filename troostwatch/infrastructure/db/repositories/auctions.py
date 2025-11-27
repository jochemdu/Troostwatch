from __future__ import annotations

import json
import sqlite3
from typing import Any, Dict, List, Optional

from ..schema import ensure_schema
from .base import BaseRepository


class AuctionRepository(BaseRepository):
    def __init__(self, conn: sqlite3.Connection) -> None:
            super().__init__(conn)
            ensure_schema(self.conn)

    def upsert(
        self,
        auction_code: str,
        auction_url: str,
        auction_title: str | None,
        pagination_pages: list[str] | None = None,
    ) -> int:
        normalized_pages = list(dict.fromkeys(pagination_pages or []))
        pages_json = json.dumps(normalized_pages) if normalized_pages else None

            self._execute(
            """
            INSERT INTO auctions (auction_code, title, url, pagination_pages)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(auction_code) DO UPDATE SET
                title = excluded.title,
                url = excluded.url,
                pagination_pages = excluded.pagination_pages
            """,
            (auction_code, auction_title, auction_url, pages_json),
        )
            auction_id = self._fetch_scalar("SELECT id FROM auctions WHERE auction_code = ?", (auction_code,))
            if not auction_id:
            raise RuntimeError("Failed to retrieve auction id after upsert")
            return int(auction_id)

    def list(self, only_active: bool = True) -> List[Dict[str, Optional[str]]]:
        query = """
            SELECT a.auction_code,
                   a.title,
                   a.url,
                   a.starts_at,
                   a.ends_at_planned,
                   SUM(CASE WHEN l.state IS NULL OR l.state NOT IN ('closed', 'ended') THEN 1 ELSE 0 END) AS active_lots,
                   COUNT(l.id) AS lot_count
            FROM auctions a
            LEFT JOIN lots l ON l.auction_id = a.id
            GROUP BY a.id
            ORDER BY a.ends_at_planned IS NULL DESC, a.ends_at_planned DESC, a.auction_code
        """
        rows = self.conn.execute(query).fetchall()
        auctions = [
            {
                "auction_code": row[0],
                "title": row[1],
                "url": row[2],
                "starts_at": row[3],
                "ends_at_planned": row[4],
                "active_lots": row[5] or 0,
                "lot_count": row[6] or 0,
            }
            for row in rows
        ]
        if not only_active:
            return auctions
        return [a for a in auctions if a["active_lots"] > 0]

    def get_by_code(self, auction_code: str) -> Optional[Dict[str, Any]]:
        """Get a single auction by code."""
        cur = self.conn.execute(
            """
            SELECT a.id, a.auction_code, a.title, a.url, a.pagination_pages,
                   a.starts_at, a.ends_at_planned,
                   COUNT(l.id) AS lot_count
            FROM auctions a
            LEFT JOIN lots l ON l.auction_id = a.id
            WHERE a.auction_code = ?
            GROUP BY a.id
            """,
            (auction_code,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "auction_code": row[1],
            "title": row[2],
            "url": row[3],
            "pagination_pages": json.loads(row[4]) if row[4] else [],
            "starts_at": row[5],
            "ends_at_planned": row[6],
            "lot_count": row[7] or 0,
        }

    def update(
        self,
        auction_code: str,
        title: Optional[str] = None,
        url: Optional[str] = None,
        starts_at: Optional[str] = None,
        ends_at_planned: Optional[str] = None,
    ) -> bool:
        """Update an auction. Returns True if updated."""
        updates = []
        params: List[Any] = []
        
        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if url is not None:
            updates.append("url = ?")
            params.append(url)
        if starts_at is not None:
            updates.append("starts_at = ?")
            params.append(starts_at)
        if ends_at_planned is not None:
            updates.append("ends_at_planned = ?")
            params.append(ends_at_planned)
        
        if not updates:
            return True
        
        params.append(auction_code)
            cur = self._execute(
            f"UPDATE auctions SET {', '.join(updates)} WHERE auction_code = ?",
            tuple(params),
        )
        self.conn.commit()
        return cur.rowcount > 0

    def delete(self, auction_code: str, delete_lots: bool = False) -> Dict[str, int]:
        """
        Delete an auction. 
        If delete_lots is True, also delete all associated lots.
        Returns dict with counts of deleted items.
        """
        # Get auction id first
            auction_id = self._fetch_scalar(
            "SELECT id FROM auctions WHERE auction_code = ?", (auction_code,)
        )
            if not auction_id:
            return {"auction": 0, "lots": 0}
        
        lots_deleted = 0
        
        if delete_lots:
            # Delete associated data first (bid_history, reference_prices, product_layers)
                lot_ids_rows = self._execute(
                    "SELECT id FROM lots WHERE auction_id = ?", (auction_id,)
                ).fetchall()
                lot_ids = [r[0] for r in lot_ids_rows]
            
            if lot_ids:
                placeholders = ",".join("?" * len(lot_ids))
                    self._execute(
                    f"DELETE FROM bid_history WHERE lot_id IN ({placeholders})",
                        tuple(lot_ids),
                )
                    self._execute(
                    f"DELETE FROM reference_prices WHERE lot_id IN ({placeholders})",
                        tuple(lot_ids),
                )
                    self._execute(
                    f"DELETE FROM product_layers WHERE lot_id IN ({placeholders})",
                        tuple(lot_ids),
                )
            
            # Delete lots
                cur = self._execute(
                "DELETE FROM lots WHERE auction_id = ?", (auction_id,)
            )
            lots_deleted = cur.rowcount
        
        # Delete the auction
            cur = self._execute(
            "DELETE FROM auctions WHERE id = ?", (auction_id,)
        )
        auction_deleted = cur.rowcount
        
        self.conn.commit()
        return {"auction": auction_deleted, "lots": lots_deleted}

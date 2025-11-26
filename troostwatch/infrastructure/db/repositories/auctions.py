from __future__ import annotations

import json
import sqlite3
from typing import Any, Dict, List, Optional

from ..schema import ensure_schema


class AuctionRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
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

        self.conn.execute(
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
        cur = self.conn.execute("SELECT id FROM auctions WHERE auction_code = ?", (auction_code,))
        row = cur.fetchone()
        if not row:
            raise RuntimeError("Failed to retrieve auction id after upsert")
        return int(row[0])

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

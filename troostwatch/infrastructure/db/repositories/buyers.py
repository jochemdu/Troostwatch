from __future__ import annotations

from typing import Dict, List, Optional

from ..schema import ensure_schema


class BuyerRepository:
    def __init__(self, conn) -> None:
        self.conn = conn
        ensure_schema(self.conn)

    def add(self, label: str, name: Optional[str] = None, notes: Optional[str] = None) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO buyers (label, name, notes) VALUES (?, ?, ?)",
            (label, name, notes),
        )
        self.conn.commit()

    def list(self) -> List[Dict[str, Optional[str]]]:
        cur = self.conn.execute("SELECT id, label, name, notes FROM buyers ORDER BY id")
        columns = [c[0] for c in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]

    def delete(self, label: str) -> None:
        self.conn.execute("DELETE FROM buyers WHERE label = ?", (label,))
        self.conn.commit()

    def get_id(self, label: str) -> Optional[int]:
        cur = self.conn.execute("SELECT id FROM buyers WHERE label = ?", (label,))
        row = cur.fetchone()
        return row[0] if row else None

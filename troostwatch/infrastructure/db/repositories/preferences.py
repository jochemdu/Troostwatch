from __future__ import annotations

import sqlite3
from typing import Optional

from ..schema import ensure_schema


class PreferenceRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        ensure_schema(self.conn)

    def get(self, key: str) -> Optional[str]:
        cur = self.conn.execute("SELECT value FROM user_preferences WHERE key = ?", (key,))
        row = cur.fetchone()
        return row[0] if row else None

    def set(self, key: str, value: Optional[str]) -> None:
        if value is None:
            self.conn.execute("DELETE FROM user_preferences WHERE key = ?", (key,))
        else:
            self.conn.execute(
                "INSERT INTO user_preferences (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )
        self.conn.commit()

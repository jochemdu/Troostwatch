from __future__ import annotations

import sqlite3
from typing import Optional

from ..schema import ensure_schema
from .base import BaseRepository


class PreferenceRepository(BaseRepository):
    def __init__(self, conn: sqlite3.Connection) -> None:
        super().__init__(conn)
        ensure_schema(self.conn)

    def get(self, key: str) -> Optional[str]:
        return self._fetch_scalar("SELECT value FROM user_preferences WHERE key = ?", (key,))

    def set(self, key: str, value: Optional[str]) -> None:
        if value is None:
            self._execute("DELETE FROM user_preferences WHERE key = ?", (key,))
        else:
            self._execute(
                "INSERT INTO user_preferences (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )
        self.conn.commit()

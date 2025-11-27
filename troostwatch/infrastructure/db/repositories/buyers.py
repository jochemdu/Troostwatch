from __future__ import annotations

import sqlite3

from ..schema import ensure_schema
from .base import BaseRepository


class DuplicateBuyerError(ValueError):
    """Raised when attempting to insert a buyer with an existing label."""


class BuyerRepository(BaseRepository):
    def __init__(self, conn: sqlite3.Connection) -> None:
        super().__init__(conn)
        ensure_schema(self.conn)

    def add(
        self, label: str, name: str | None = None, notes: str | None = None
    ) -> None:
        cursor = self._execute(
            "INSERT OR IGNORE INTO buyers (label, name, notes) VALUES (?, ?, ?)",
            (label, name, notes),
        )
        self.conn.commit()

        if cursor.rowcount == 0:
            raise DuplicateBuyerError(f"Buyer label '{label}' already exists")

    def list(self) -> list[dict[str, int | str | None]]:
        return self._fetch_all_as_dicts(
            "SELECT id, label, name, notes FROM buyers ORDER BY id"
        )

    def delete(self, label: str) -> None:
        self._execute("DELETE FROM buyers WHERE label = ?", (label,))
        self.conn.commit()

    def get_id(self, label: str) -> int | None:
        return self._fetch_scalar("SELECT id FROM buyers WHERE label = ?", (label,))

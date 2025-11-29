from __future__ import annotations

from pathlib import Path


_SCHEMA_FILE = Path(__file__).resolve().parents[4] / "schema" / "schema.sql"


def ensure_core_schema(conn) -> None:
    """Apply the core schema from ``schema/schema.sql`` if available."""

    if not _SCHEMA_FILE.exists():
        return
    with open(_SCHEMA_FILE, "r", encoding="utf-8") as f:
        conn.executescript(f.read())

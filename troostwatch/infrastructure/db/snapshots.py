from __future__ import annotations

import sqlite3
from pathlib import Path

from .config import get_path_config
from .connection import iso_utcnow


def create_snapshot(
    source_db: str | Path,
    *,
    snapshot_root: str | Path | None = None,
    label: str | None = None,
) -> Path:
    """Create a SQLite backup using :meth:`sqlite3.Connection.backup`."""

    paths = get_path_config()
    root = Path(
        snapshot_root) if snapshot_root is not None else paths["snapshots_root"]
    root.mkdir(parents=True, exist_ok=True)
    timestamp = iso_utcnow().replace(":", "-")
    suffix = label or "snapshot"
    destination = root / f"{suffix}-{timestamp}.db"
    with sqlite3.connect(source_db) as src, sqlite3.connect(destination) as dst:
        src.backup(dst)
    return destination

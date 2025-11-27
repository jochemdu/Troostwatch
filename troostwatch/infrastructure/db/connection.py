from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .config import get_default_timeout, get_path_config, load_config


def iso_utcnow() -> str:
    """Return an ISO‑8601 timestamp in UTC with ``Z`` suffix."""

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def apply_pragmas(
    conn: sqlite3.Connection,
    *,
    enable_wal: bool = True,
    foreign_keys: bool = True,
    busy_timeout_ms: int | None = None,
) -> None:
    """Apply SQLite PRAGMAs required by Troostwatch."""

    if enable_wal:
        conn.execute("PRAGMA journal_mode=WAL;")
    if foreign_keys:
        conn.execute("PRAGMA foreign_keys=ON;")
    if busy_timeout_ms is not None:
        conn.execute(f"PRAGMA busy_timeout={int(busy_timeout_ms)};")


@contextmanager
def get_connection(
    db_path: str | Path | None = None,
    *,
    timeout: float | None = None,
    enable_wal: bool | None = None,
    foreign_keys: bool | None = None,
    check_same_thread: bool = True,
) -> Iterator[sqlite3.Connection]:
    """Yield a configured SQLite connection."""

    paths = get_path_config()
    resolved_db_path = Path(db_path) if db_path is not None else paths["db_path"]
    resolved_db_path.parent.mkdir(parents=True, exist_ok=True)
    timeout_value = timeout if timeout is not None else get_default_timeout()
    conn = sqlite3.connect(
        resolved_db_path, timeout=timeout_value, check_same_thread=check_same_thread
    )
    try:
        cfg = load_config()
        db_cfg = cfg.get("db", {}) if isinstance(cfg, dict) else {}
        resolved_enable_wal = enable_wal if enable_wal is not None else bool(db_cfg.get("enable_wal", True))
        resolved_foreign_keys = foreign_keys if foreign_keys is not None else bool(db_cfg.get("foreign_keys", True))
        apply_pragmas(
            conn,
            enable_wal=resolved_enable_wal,
            foreign_keys=resolved_foreign_keys,
            busy_timeout_ms=int(timeout_value * 1000),
        )
        yield conn
    finally:
        conn.close()

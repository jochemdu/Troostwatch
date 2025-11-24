"""Database utilities for Troostwatch.

This module centralises database access for the project. It handles loading
default paths from :mod:`config.json`, opening SQLite connections with the
required PRAGMAs, applying the core schema plus project specific tables and
provides convenience helpers for snapshots/backups.
"""

from __future__ import annotations

import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Iterable, Optional, List, Dict, Any

SCHEMA_BUYERS_SQL = """
CREATE TABLE IF NOT EXISTS buyers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT NOT NULL UNIQUE,
    name TEXT,
    notes TEXT
);
"""

SCHEMA_POSITIONS_SQL = """
CREATE TABLE IF NOT EXISTS my_lot_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    buyer_id INTEGER NOT NULL,
    lot_id INTEGER NOT NULL,
    track_active INTEGER NOT NULL DEFAULT 1,
    max_budget_total_eur REAL,
    my_highest_bid_eur REAL,
    FOREIGN KEY (buyer_id) REFERENCES buyers (id) ON DELETE CASCADE,
    FOREIGN KEY (lot_id) REFERENCES lots (id) ON DELETE CASCADE,
    UNIQUE (buyer_id, lot_id)
);
"""

SCHEMA_MY_BIDS_SQL = """
CREATE TABLE IF NOT EXISTS my_bids (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lot_id INTEGER NOT NULL,
    buyer_id INTEGER,
    amount_eur REAL NOT NULL,
    placed_at TEXT NOT NULL,
    note TEXT,
    FOREIGN KEY (lot_id) REFERENCES lots (id) ON DELETE CASCADE,
    FOREIGN KEY (buyer_id) REFERENCES buyers (id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_my_bids_lot_id ON my_bids (lot_id);
"""

SCHEMA_PRODUCT_LAYERS_SQL = """
CREATE TABLE IF NOT EXISTS product_layers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lot_id INTEGER NOT NULL,
    layer INTEGER NOT NULL DEFAULT 0,
    title TEXT,
    value TEXT,
    FOREIGN KEY (lot_id) REFERENCES lots (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_product_layers_lot_id ON product_layers (lot_id);
"""

SCHEMA_SYNC_RUNS_SQL = """
CREATE TABLE IF NOT EXISTS sync_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    auction_code TEXT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT,
    pages_scanned INTEGER DEFAULT 0,
    lots_scanned INTEGER DEFAULT 0,
    lots_updated INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    max_pages INTEGER,
    dry_run INTEGER,
    notes TEXT
);
CREATE INDEX IF NOT EXISTS idx_sync_runs_auction_code ON sync_runs (auction_code);
"""

SCHEMA_MIGRATIONS_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    applied_at TEXT NOT NULL,
    notes TEXT
);
"""

# Relative path to the core schema used by sync operations. This includes
# definitions for auctions and lots tables. We compute the path relative to
# this file so it works regardless of the working directory from which
# functions are invoked.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCHEMA_FILE = _REPO_ROOT / "schema" / "schema.sql"
_CONFIG_FILE = _REPO_ROOT / "config.json"

DEFAULT_DB_TIMEOUT = 30.0


def _load_config(config_path: Path | str | None = None) -> Dict[str, Any]:
    """Load ``config.json`` if present and return it as a dictionary.

    A missing config file is tolerated; defaults are returned instead. Paths
    from the config are resolved relative to the repository root when they are
    not absolute.
    """

    path = Path(config_path) if config_path is not None else _CONFIG_FILE
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_config(config_path: Path | str | None = None) -> Dict[str, Any]:
    """Return the loaded project configuration as a dictionary.

    This is a light wrapper around the internal loader so other modules can
    easily access configuration values without duplicating path resolution
    logic.
    """

    return _load_config(config_path)


def _ensure_user_preferences(conn: sqlite3.Connection) -> None:
    """Create a simple key/value table for user preferences if missing."""

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS user_preferences (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """
    )


def get_path_config(config_path: Path | str | None = None) -> Dict[str, Path]:
    """Return resolved filesystem paths from the project configuration.

    The configuration file is optional; sensible defaults (e.g. ``troostwatch.db``
    in the repository root) are supplied when values are missing. All returned
    paths are absolute :class:`pathlib.Path` objects.
    """

    cfg = _load_config(config_path)
    root = Path(config_path).parent if config_path is not None else _CONFIG_FILE.parent
    defaults = {
        "db_path": root / "troostwatch.db",
        "snapshots_root": root / "snapshots",
        "lot_cards_dir": root / "snapshots" / "lot_cards",
        "lot_details_dir": root / "snapshots" / "lot_details",
    }
    paths_cfg = cfg.get("paths", {}) if isinstance(cfg.get("paths", {}), dict) else {}
    resolved: Dict[str, Path] = {}
    for key, default_value in defaults.items():
        raw_value = paths_cfg.get(key, default_value)
        resolved_value = Path(raw_value)
        if not resolved_value.is_absolute():
            resolved_value = (root / resolved_value).resolve()
        resolved[key] = resolved_value
    return resolved


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
    """Apply SQLite PRAGMAs required by Troostwatch.

    The defaults enable WAL for concurrency, enforce foreign keys and set an
    optional ``busy_timeout`` to handle contention gracefully.
    """

    if enable_wal:
        conn.execute("PRAGMA journal_mode=WAL;")
    if foreign_keys:
        conn.execute("PRAGMA foreign_keys=ON;")
    if busy_timeout_ms is not None:
        conn.execute(f"PRAGMA busy_timeout={int(busy_timeout_ms)};")


def get_default_timeout(config_path: Path | str | None = None) -> float:
    """Read the preferred database timeout from configuration."""

    cfg = _load_config(config_path)
    try:
        return float(cfg.get("db_timeout_seconds", DEFAULT_DB_TIMEOUT))
    except (TypeError, ValueError):
        return DEFAULT_DB_TIMEOUT


@contextmanager
def get_connection(
    db_path: str | Path | None = None,
    *,
    timeout: float | None = None,
    enable_wal: bool | None = None,
    foreign_keys: bool | None = None,
) -> Iterator[sqlite3.Connection]:
    """Yield a configured SQLite connection.

    The helper resolves the database path from ``config.json`` when ``db_path``
    is ``None``, creates parent directories when needed, applies WAL and
    ``foreign_keys`` PRAGMAs and honours a configurable timeout.
    """

    paths = get_path_config()
    resolved_db_path = Path(db_path) if db_path is not None else paths["db_path"]
    resolved_db_path.parent.mkdir(parents=True, exist_ok=True)
    timeout_value = timeout if timeout is not None else get_default_timeout()
    conn = sqlite3.connect(resolved_db_path, timeout=timeout_value)
    try:
        # Resolve pragma defaults from configuration when callers pass None.
        cfg = _load_config()
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


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Apply the full database schema (core + project specific tables).

    Besides the core schema from ``schema/schema.sql`` this also ensures the
    presence of ``buyers``, ``my_lot_positions``, ``my_bids``,
    ``product_layers`` and ``sync_runs`` tables used throughout the project.
    """

    ensure_core_schema(conn)
    # Ensure we have a migrations table so we can record applied updates.
    conn.executescript(SCHEMA_MIGRATIONS_SQL)
    # Apply any SQL files from the `migrations/` directory in repository root.
    _apply_migration_dir(conn)
    _ensure_auction_columns(conn)
    # Ensure legacy databases get the expected columns on `lots` as a
    # defensive fallback for older DBs or when the migration runner is
    # unavailable for some reason.
    _ensure_lots_columns(conn)
    _ensure_hash_columns(conn)
    conn.executescript(SCHEMA_BUYERS_SQL)
    conn.executescript(SCHEMA_POSITIONS_SQL)
    conn.executescript(SCHEMA_MY_BIDS_SQL)
    conn.executescript(SCHEMA_PRODUCT_LAYERS_SQL)
    conn.executescript(SCHEMA_SYNC_RUNS_SQL)
    _ensure_user_preferences(conn)
    _ensure_hash_columns(conn)


def ensure_core_schema(conn: sqlite3.Connection) -> None:
    """Apply the core schema from ``schema/schema.sql`` if available."""

    if not _SCHEMA_FILE.exists():
        return
    with open(_SCHEMA_FILE, "r", encoding="utf-8") as f:
        conn.executescript(f.read())


def _ensure_lots_columns(conn: sqlite3.Connection) -> None:
    """Add missing columns to the ``lots`` table when migrating older DBs.

    The project uses ALTER TABLE ADD COLUMN to add any columns that are
    referenced by upserts but may be missing in older copies of ``troostwatch.db``.
    This function is idempotent and will no-op when columns already exist.
    """
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lots'")
    if cur.fetchone() is None:
        # No lots table yet; core schema not applied.
        return

    existing = {row[1] for row in conn.execute("PRAGMA table_info(lots)").fetchall()}

    to_add = {
        "status": "TEXT",
        "opens_at": "TEXT",
        "closing_time_current": "TEXT",
        "closing_time_original": "TEXT",
        "bid_count": "INTEGER",
        "opening_bid_eur": "REAL",
        "current_bid_eur": "REAL",
        "current_bidder_label": "TEXT",
        "current_bid_buyer_id": "INTEGER",
        "buyer_fee_percent": "REAL",
        "buyer_fee_vat_percent": "REAL",
        "vat_percent": "REAL",
        "awarding_state": "TEXT",
        "total_example_price_eur": "REAL",
        "location_city": "TEXT",
        "location_country": "TEXT",
        "seller_allocation_note": "TEXT",
    }

    added_cols: list[str] = []
    for col, col_type in to_add.items():
        if col in existing:
            continue
        # ALTER TABLE ADD COLUMN is safe for SQLite and will use NULL as default.
        conn.execute(f"ALTER TABLE lots ADD COLUMN {col} {col_type}")
        added_cols.append(col)
    # If we added one or more columns, record the migration so we don't
    # repeatedly insert the same migration marker. This is intentionally
    # simple: a single migration name covers the first batch of added cols.
    if added_cols:
        migration_name = "add_lots_columns_v1"
        cur = conn.execute("SELECT 1 FROM schema_migrations WHERE name = ?", (migration_name,))
        if cur.fetchone() is None:
            conn.execute(
                "INSERT INTO schema_migrations (name, applied_at, notes) VALUES (?, ?, ?)",
                (migration_name, iso_utcnow(), ",".join(added_cols)),
            )


def _ensure_auction_columns(conn: sqlite3.Connection) -> None:
    """Add pagination tracking columns to the ``auctions`` table if missing."""

    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='auctions'")
    if cur.fetchone() is None:
        return

    existing = {row[1] for row in conn.execute("PRAGMA table_info(auctions)").fetchall()}
    added_cols: list[str] = []
    if "pagination_pages" not in existing:
        conn.execute("ALTER TABLE auctions ADD COLUMN pagination_pages TEXT")
        added_cols.append("pagination_pages")

    if added_cols:
        migration_name = "add_auction_pagination_pages_v1"
        cur = conn.execute("SELECT 1 FROM schema_migrations WHERE name = ?", (migration_name,))
        if cur.fetchone() is None:
            conn.execute(
                "INSERT INTO schema_migrations (name, applied_at, notes) VALUES (?, ?, ?)",
                (migration_name, iso_utcnow(), ",".join(added_cols)),
            )


def _apply_migration_dir(conn: sqlite3.Connection, migrations_dir: str | None = None) -> None:
    """Apply SQL migration files from the repository `migrations/` directory.

    Files are applied in lexical order. Each applied filename is recorded in
    `schema_migrations` (name == filename) to ensure idempotence.
    """
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    migrations_path = Path(migrations_dir) if migrations_dir else (root / "migrations")
    if not migrations_path.exists() or not migrations_path.is_dir():
        return

    for path in sorted(migrations_path.iterdir()):
        if not path.is_file() or not path.name.lower().endswith(".sql"):
            continue
        name = path.name
        cur = conn.execute("SELECT 1 FROM schema_migrations WHERE name = ?", (name,))
        if cur.fetchone() is not None:
            continue
        with open(path, "r", encoding="utf-8") as f:
            sql = f.read()
        if not sql.strip():
            continue
        conn.executescript(sql)
        conn.execute(
            "INSERT INTO schema_migrations (name, applied_at, notes) VALUES (?, ?, ?)",
            (name, iso_utcnow(), f"applied from {path.relative_to(root)}"),
        )
    # commit is left to the caller; callers of ensure_schema generally commit as needed
def _ensure_hash_columns(conn: sqlite3.Connection) -> None:
    """Add hash- and timestamp-related columns to the lots table if missing."""

    required_columns = {
        "listing_hash": "TEXT",
        "detail_hash": "TEXT",
        "last_seen_at": "TEXT",
        "detail_last_seen_at": "TEXT",
    }
    cur = conn.execute("PRAGMA table_info(lots)")
    existing = {row[1] for row in cur.fetchall()}
    for column, sql_type in required_columns.items():
        if column not in existing:
            conn.execute(f"ALTER TABLE lots ADD COLUMN {column} {sql_type}")



def run_migrations(conn: sqlite3.Connection, migrations: Iterable[str] | None = None) -> None:
    """Execute bundled schema and any additional migration scripts.

    Pass an iterable of SQL strings to run project‑specific migrations after
    the baseline schema is in place.
    """

    ensure_schema(conn)
    if migrations:
        for script in migrations:
            conn.executescript(script)


def create_snapshot(
    source_db: str | Path,
    *,
    snapshot_root: str | Path | None = None,
    label: str | None = None,
) -> Path:
    """Create a SQLite backup using :meth:`sqlite3.Connection.backup`.

    The snapshot directory is resolved from ``config.json`` when not provided.
    The resulting filename includes an ISO‑8601 timestamp to guarantee
    uniqueness and the created :class:`pathlib.Path` is returned for
    downstream use.
    """

    paths = get_path_config()
    root = Path(snapshot_root) if snapshot_root is not None else paths["snapshots_root"]
    root.mkdir(parents=True, exist_ok=True)
    timestamp = iso_utcnow().replace(":", "-")
    suffix = label or "snapshot"
    destination = root / f"{suffix}-{timestamp}.db"
    with sqlite3.connect(source_db) as src, sqlite3.connect(destination) as dst:
        src.backup(dst)
    return destination


def add_buyer(conn: sqlite3.Connection, label: str, name: Optional[str] = None, notes: Optional[str] = None) -> None:
    """Add a buyer to the database.

    If a buyer with the same label already exists, this function does nothing.

    Args:
        conn: Open sqlite3.Connection.
        label: Unique label for the buyer.
        name: Optional full name of the buyer.
        notes: Optional free‑form notes.
    """
    ensure_schema(conn)
    conn.execute(
        "INSERT OR IGNORE INTO buyers (label, name, notes) VALUES (?, ?, ?)",
        (label, name, notes),
    )
    conn.commit()


def list_buyers(conn: sqlite3.Connection) -> List[Dict[str, Optional[str]]]:
    """Return a list of all buyers in the database.

    Args:
        conn: Open sqlite3.Connection.

    Returns:
        A list of dictionaries with keys: id, label, name, notes.
    """
    ensure_schema(conn)
    cur = conn.execute("SELECT id, label, name, notes FROM buyers ORDER BY id")
    columns = [c[0] for c in cur.description]
    return [dict(zip(columns, row)) for row in cur.fetchall()]


def delete_buyer(conn: sqlite3.Connection, label: str) -> None:
    """Delete a buyer from the database by label.

    Args:
        conn: Open sqlite3.Connection.
        label: The label of the buyer to remove.
    """
    ensure_schema(conn)
    conn.execute("DELETE FROM buyers WHERE label = ?", (label,))
    conn.commit()

# Position management helpers

def _get_buyer_id(conn: sqlite3.Connection, label: str) -> Optional[int]:
    """Return the row ID of a buyer given its label, or None if not found."""
    ensure_schema(conn)
    cur = conn.execute("SELECT id FROM buyers WHERE label = ?", (label,))
    row = cur.fetchone()
    return row[0] if row else None

def _get_lot_id(conn: sqlite3.Connection, lot_code: str, auction_code: Optional[str] = None) -> Optional[int]:
    """Return the row ID of a lot given its lot code and optional auction code.

    If multiple lots share the same lot code across auctions and an auction code
    is not provided, the first matching lot ID is returned. None is returned if
    no matching lot is found.
    """
    ensure_core_schema(conn)
    query = "SELECT l.id FROM lots l JOIN auctions a ON l.auction_id = a.id WHERE l.lot_code = ?"

    def _lookup(code: str) -> Optional[int]:
        params: List = [code]
        local_query = query
        if auction_code is not None:
            local_query += " AND a.auction_code = ?"
            params.append(auction_code)
        cur = conn.execute(local_query, tuple(params))
        row = cur.fetchone()
        return row[0] if row else None

    lot_id = _lookup(lot_code)
    if lot_id is None and auction_code and not lot_code.startswith(f"{auction_code}-"):
        lot_id = _lookup(f"{auction_code}-{lot_code}")
    return lot_id

def add_position(
    conn: sqlite3.Connection,
    buyer_label: str,
    lot_code: str,
    auction_code: Optional[str] = None,
    track_active: bool = True,
    max_budget_total_eur: Optional[float] = None,
    my_highest_bid_eur: Optional[float] = None,
) -> None:
    """Insert or update a lot position for the given buyer and lot.

    Args:
        conn: An open SQLite connection.
        buyer_label: Label of the buyer who owns the position.
        lot_code: The code of the lot to track.
        auction_code: Optional auction code to disambiguate lots.
        track_active: Whether this lot should be included in exposure calculations.
        max_budget_total_eur: Optional maximum total budget for the lot.
        my_highest_bid_eur: Optional highest bid placed by the buyer on this lot.
    """
    ensure_schema(conn)
    buyer_id = _get_buyer_id(conn, buyer_label)
    if buyer_id is None:
        raise ValueError(f"Buyer with label '{buyer_label}' does not exist")
    lot_id = _get_lot_id(conn, lot_code, auction_code)
    if lot_id is None:
        raise ValueError(f"Lot with code '{lot_code}' not found (auction: {auction_code})")
    # Upsert logic: insert or replace existing record
    conn.execute(
        """
        INSERT INTO my_lot_positions (buyer_id, lot_id, track_active, max_budget_total_eur, my_highest_bid_eur)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(buyer_id, lot_id) DO UPDATE SET
            track_active = excluded.track_active,
            max_budget_total_eur = excluded.max_budget_total_eur,
            my_highest_bid_eur = excluded.my_highest_bid_eur
        """,
        (buyer_id, lot_id, 1 if track_active else 0, max_budget_total_eur, my_highest_bid_eur),
    )
    conn.commit()

def list_positions(conn: sqlite3.Connection, buyer_label: Optional[str] = None) -> List[Dict[str, Optional[str]]]:
    """Return a list of positions optionally filtered by buyer label.

    Args:
        conn: An open SQLite connection.
        buyer_label: If provided, only positions for this buyer are returned.

    Returns:
        A list of dictionaries describing each position, including buyer label,
        auction code, lot code, track_active flag and budget fields.
    """
    ensure_schema(conn)
    params: List = []
    query = """
        SELECT b.label AS buyer_label,
               a.auction_code AS auction_code,
               l.lot_code AS lot_code,
               p.track_active,
               p.max_budget_total_eur,
               p.my_highest_bid_eur,
               l.title AS lot_title,
               l.state AS lot_state,
               l.current_bid_eur
        FROM my_lot_positions p
        JOIN buyers b ON p.buyer_id = b.id
        JOIN lots l ON p.lot_id = l.id
        JOIN auctions a ON l.auction_id = a.id
    """
    if buyer_label:
        query += " WHERE b.label = ?"
        params.append(buyer_label)
    query += " ORDER BY a.auction_code, l.lot_code"
    cur = conn.execute(query, tuple(params))
    columns = [c[0] for c in cur.description]
    return [dict(zip(columns, row)) for row in cur.fetchall()]

def delete_position(conn: sqlite3.Connection, buyer_label: str, lot_code: str, auction_code: Optional[str] = None) -> None:
    """Remove a tracked position for a buyer and lot.

    Args:
        conn: An open SQLite connection.
        buyer_label: The label of the buyer.
        lot_code: The code of the lot.
        auction_code: Optional auction code to disambiguate lots.
    """
    ensure_schema(conn)
    buyer_id = _get_buyer_id(conn, buyer_label)
    if buyer_id is None:
        raise ValueError(f"Buyer with label '{buyer_label}' does not exist")
    lot_id = _get_lot_id(conn, lot_code, auction_code)
    if lot_id is None:
        raise ValueError(f"Lot with code '{lot_code}' not found (auction: {auction_code})")
    conn.execute(
        "DELETE FROM my_lot_positions WHERE buyer_id = ? AND lot_id = ?",
        (buyer_id, lot_id),
    )
    conn.commit()


def list_auctions(conn: sqlite3.Connection, only_active: bool = True) -> List[Dict[str, Optional[str]]]:
    """Return auctions, optionally limited to those with active lots."""

    ensure_schema(conn)
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
    rows = conn.execute(query).fetchall()
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
    active = [a for a in auctions if a["active_lots"] > 0]
    return active


def list_lot_codes_by_auction(conn: sqlite3.Connection, auction_code: str) -> List[str]:
    """Return lot codes for a given auction, ordered numerically when possible."""

    ensure_schema(conn)
    rows = conn.execute(
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


def get_preference(conn: sqlite3.Connection, key: str) -> Optional[str]:
    """Return a stored preference value for the given key."""

    ensure_schema(conn)
    _ensure_user_preferences(conn)
    cur = conn.execute("SELECT value FROM user_preferences WHERE key = ?", (key,))
    row = cur.fetchone()
    return row[0] if row else None


def set_preference(conn: sqlite3.Connection, key: str, value: Optional[str]) -> None:
    """Persist a preference key/value pair (removing it when value is None)."""

    ensure_schema(conn)
    _ensure_user_preferences(conn)
    if value is None:
        conn.execute("DELETE FROM user_preferences WHERE key = ?", (key,))
    else:
        conn.execute(
            "INSERT INTO user_preferences (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
    conn.commit()


def list_lots(
    conn: sqlite3.Connection,
    *,
    auction_code: Optional[str] = None,
    state: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[Dict[str, Optional[str]]]:
    """Return lots optionally filtered by auction code or state.

    Args:
        conn: An open SQLite connection.
        auction_code: If provided, only include lots from this auction code.
        state: If provided, filter by the lot's ``state`` column.
        limit: Maximum number of rows to return; ``None`` disables the limit.

    Returns:
        A list of dictionaries describing each lot, including auction code,
        lot code, title, state, bid metrics and closing times.
    """

    ensure_schema(conn)

    query = """
        SELECT a.auction_code AS auction_code,
               l.lot_code AS lot_code,
               l.title AS title,
               l.state AS state,
               l.current_bid_eur AS current_bid_eur,
               l.bid_count AS bid_count,
               l.current_bidder_label AS current_bidder_label,
               l.closing_time_current AS closing_time_current,
               l.closing_time_original AS closing_time_original
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
    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY a.auction_code, l.lot_code"
    if limit is not None:
        query += " LIMIT ?"
        params.append(limit)

    cur = conn.execute(query, tuple(params))
    columns = [c[0] for c in cur.description]
    return [dict(zip(columns, row)) for row in cur.fetchall()]
from __future__ import annotations

from .core import ensure_core_schema
from .migrations import SchemaMigrator
from .tables import (
    SCHEMA_BUYERS_SQL,
    SCHEMA_MY_BIDS_SQL,
    SCHEMA_POSITIONS_SQL,
    SCHEMA_PRODUCT_LAYERS_SQL,
    SCHEMA_SYNC_RUNS_SQL,
    SCHEMA_USER_PREFERENCES_SQL,
)


def ensure_schema(conn) -> None:
    """Apply the full database schema (core + project specific tables)."""

    ensure_core_schema(conn)
    migrator = SchemaMigrator(conn)
    migrator.ensure_table()
    migrator.apply_path()
    migrator.ensure_current_version()
    _ensure_auction_columns(conn, migrator)
    _ensure_lots_columns(conn, migrator)
    _ensure_hash_columns(conn)
    conn.executescript(SCHEMA_BUYERS_SQL)
    conn.executescript(SCHEMA_POSITIONS_SQL)
    conn.executescript(SCHEMA_MY_BIDS_SQL)
    conn.executescript(SCHEMA_PRODUCT_LAYERS_SQL)
    conn.executescript(SCHEMA_SYNC_RUNS_SQL)
    conn.executescript(SCHEMA_USER_PREFERENCES_SQL)


def _ensure_lots_columns(conn, migrator: SchemaMigrator) -> None:
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lots'")
    if cur.fetchone() is None:
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
        conn.execute(f"ALTER TABLE lots ADD COLUMN {col} {col_type}")
        added_cols.append(col)
    if added_cols:
        migration_name = "add_lots_columns_v1"
        if not migrator.has_migration(migration_name):
            migrator.record(migration_name, ",".join(added_cols))


def _ensure_auction_columns(conn, migrator: SchemaMigrator) -> None:
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
        if not migrator.has_migration(migration_name):
            migrator.record(migration_name, ",".join(added_cols))


def _ensure_hash_columns(conn) -> None:
    required_columns = {
        "listing_hash": "TEXT",
        "detail_hash": "TEXT",
        "last_seen_at": "TEXT",
        "detail_last_seen_at": "TEXT",
    }
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lots'")
    if cur.fetchone() is None:
        return
    cur = conn.execute("PRAGMA table_info(lots)")
    existing = {row[1] for row in cur.fetchall()}
    for column, sql_type in required_columns.items():
        if column not in existing:
            conn.execute(f"ALTER TABLE lots ADD COLUMN {column} {sql_type}")

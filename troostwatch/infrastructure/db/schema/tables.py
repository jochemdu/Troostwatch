from __future__ import annotations

SCHEMA_VERSION_SQL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);
"""

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

SCHEMA_USER_PREFERENCES_SQL = """
CREATE TABLE IF NOT EXISTS user_preferences (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""

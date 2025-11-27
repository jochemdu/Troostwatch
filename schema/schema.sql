-- Troostwatch schema version: 3
-- SQLite schema for Troostwatch
--
-- This file is the canonical source of truth for new databases. The schema
-- version above must be incremented whenever structural changes are made.
-- See docs/migration_policy.md for the full migration workflow.

BEGIN TRANSACTION;

-- Schema version tracking table - records the semantic version applied to this
-- database. Only one row should exist at any time.
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS auctions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    auction_code TEXT NOT NULL UNIQUE,
    title TEXT,
    url TEXT,
    pagination_pages TEXT,
    starts_at TEXT,
    ends_at_planned TEXT
);

CREATE TABLE IF NOT EXISTS buyers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT NOT NULL UNIQUE,
    name TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS user_preferences (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT UNIQUE,
    title TEXT NOT NULL,
    description TEXT,
    category TEXT
);

CREATE TABLE IF NOT EXISTS product_specs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    spec_key TEXT NOT NULL,
    spec_value TEXT,
    FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE,
    UNIQUE (product_id, spec_key)
);

CREATE INDEX IF NOT EXISTS idx_product_specs_product_id ON product_specs (product_id);

CREATE TABLE IF NOT EXISTS lots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    auction_id INTEGER NOT NULL,
    lot_code TEXT NOT NULL,
    title TEXT,
    url TEXT,
    state TEXT,
    status TEXT,
    opens_at TEXT,
    closing_time_current TEXT,
    closing_time_original TEXT,
    bid_count INTEGER,
    opening_bid_eur REAL,
    current_bid_eur REAL,
    current_bidder_label TEXT,
    current_bid_buyer_id INTEGER,
    buyer_fee_percent REAL,
    buyer_fee_vat_percent REAL,
    vat_percent REAL,
    awarding_state TEXT,
    total_example_price_eur REAL,
    location_city TEXT,
    location_country TEXT,
    seller_allocation_note TEXT,
    brand TEXT,
    reference_price_new_eur REAL,
    reference_price_used_eur REAL,
    reference_source TEXT,
    reference_url TEXT,
    notes TEXT,
    listing_hash TEXT,
    detail_hash TEXT,
    last_seen_at TEXT,
    detail_last_seen_at TEXT,
    FOREIGN KEY (auction_id) REFERENCES auctions (id) ON DELETE CASCADE,
    FOREIGN KEY (current_bid_buyer_id) REFERENCES buyers (id),
    UNIQUE (auction_id, lot_code)
);

CREATE INDEX IF NOT EXISTS idx_lots_auction_id ON lots (auction_id);
CREATE INDEX IF NOT EXISTS idx_lots_current_bid_buyer_id ON lots (current_bid_buyer_id);

-- Table storing the positions a buyer has on individual lots. Each record
-- indicates that a buyer is actively tracking a specific lot and may place
-- bids up to a configured maximum budget. The track_active flag controls
-- whether a lot is included in exposure calculations. A unique index on
-- (buyer_id, lot_id) prevents duplicate entries for the same buyer/lot.
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

CREATE INDEX IF NOT EXISTS idx_my_lot_positions_buyer_id ON my_lot_positions (buyer_id);
CREATE INDEX IF NOT EXISTS idx_my_lot_positions_lot_id ON my_lot_positions (lot_id);

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

CREATE TABLE IF NOT EXISTS bid_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lot_id INTEGER NOT NULL,
    bidder_label TEXT NOT NULL,
    amount_eur REAL NOT NULL,
    bid_time TEXT,
    FOREIGN KEY (lot_id) REFERENCES lots (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_bid_history_lot_id ON bid_history (lot_id);

CREATE TABLE IF NOT EXISTS lot_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lot_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity REAL NOT NULL DEFAULT 1,
    unit TEXT,
    extra_cost_eur REAL,
    extra_cost_description TEXT,
    FOREIGN KEY (lot_id) REFERENCES lots (id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE,
    UNIQUE (lot_id, product_id)
);

CREATE INDEX IF NOT EXISTS idx_lot_items_lot_id ON lot_items (lot_id);
CREATE INDEX IF NOT EXISTS idx_lot_items_product_id ON lot_items (product_id);

CREATE TABLE IF NOT EXISTS market_offers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lot_id INTEGER NOT NULL,
    buyer_id INTEGER,
    offer_amount_eur REAL,
    offer_state TEXT,
    created_at TEXT,
    updated_at TEXT,
    FOREIGN KEY (lot_id) REFERENCES lots (id) ON DELETE CASCADE,
    FOREIGN KEY (buyer_id) REFERENCES buyers (id)
);

CREATE INDEX IF NOT EXISTS idx_market_offers_lot_id ON market_offers (lot_id);
CREATE INDEX IF NOT EXISTS idx_market_offers_buyer_id ON market_offers (buyer_id);

CREATE TABLE IF NOT EXISTS product_layers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lot_id INTEGER NOT NULL,
    layer INTEGER NOT NULL DEFAULT 0,
    title TEXT,
    value TEXT,
    FOREIGN KEY (lot_id) REFERENCES lots (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_product_layers_lot_id ON product_layers (lot_id);

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

CREATE TABLE IF NOT EXISTS schema_migrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    applied_at TEXT NOT NULL,
    notes TEXT
);

COMMIT;

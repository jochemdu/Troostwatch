-- SQLite schema for Troostwatch
-- This is a simplified placeholder schema. The actual project should
-- define the full schema with all tables, indexes and relationships.

BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS auctions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    auction_code TEXT NOT NULL UNIQUE,
    title TEXT,
    url TEXT,
    starts_at TEXT,
    ends_at_planned TEXT
);

CREATE TABLE IF NOT EXISTS buyers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT NOT NULL UNIQUE,
    name TEXT,
    notes TEXT
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
    current_bid_buyer_id INTEGER,
    buyer_fee_percent REAL,
    vat_percent REAL,
    awarding_state TEXT,
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
    exposure_limit_eur REAL,
    status TEXT,
    FOREIGN KEY (buyer_id) REFERENCES buyers (id) ON DELETE CASCADE,
    FOREIGN KEY (lot_id) REFERENCES lots (id) ON DELETE CASCADE,
    UNIQUE (buyer_id, lot_id)
);

CREATE INDEX IF NOT EXISTS idx_my_lot_positions_buyer_id ON my_lot_positions (buyer_id);
CREATE INDEX IF NOT EXISTS idx_my_lot_positions_lot_id ON my_lot_positions (lot_id);

CREATE TABLE IF NOT EXISTS my_bids (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    buyer_id INTEGER NOT NULL,
    lot_id INTEGER NOT NULL,
    bid_amount_eur REAL NOT NULL,
    bid_time TEXT,
    is_proxy INTEGER NOT NULL DEFAULT 0,
    status TEXT,
    FOREIGN KEY (buyer_id) REFERENCES buyers (id) ON DELETE CASCADE,
    FOREIGN KEY (lot_id) REFERENCES lots (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_my_bids_lot_id ON my_bids (lot_id);
CREATE INDEX IF NOT EXISTS idx_my_bids_buyer_id ON my_bids (buyer_id);

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

CREATE TABLE IF NOT EXISTS sync_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT,
    started_at TEXT,
    finished_at TEXT,
    state TEXT,
    notes TEXT
);

-- Additional tables (buyers, my_lot_positions, my_bids, products, etc.)
-- should be added here following the full specification of the project.

COMMIT;

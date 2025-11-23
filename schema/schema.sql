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

CREATE TABLE IF NOT EXISTS lots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    auction_id INTEGER NOT NULL,
    lot_code TEXT NOT NULL,
    title TEXT,
    url TEXT,
    state TEXT,
    opens_at TEXT,
    closing_time_current TEXT,
    closing_time_original TEXT,
    bid_count INTEGER,
    current_bid_eur REAL,
    FOREIGN KEY (auction_id) REFERENCES auctions (id) ON DELETE CASCADE
);

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

-- Additional tables (buyers, my_lot_positions, my_bids, products, etc.)
-- should be added here following the full specification of the project.

COMMIT;
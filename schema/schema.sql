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

-- Additional tables (buyers, my_lot_positions, my_bids, products, etc.)
-- should be added here following the full specification of the project.

COMMIT;
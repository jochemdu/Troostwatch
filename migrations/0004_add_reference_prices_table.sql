-- Migration: Add reference_prices table for multiple reference prices per lot
-- This replaces the single reference_price columns on the lots table

CREATE TABLE IF NOT EXISTS reference_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lot_id INTEGER NOT NULL,
    condition TEXT NOT NULL DEFAULT 'used',  -- 'new', 'used', 'refurbished'
    price_eur REAL NOT NULL,
    source TEXT,                              -- e.g. 'Marktplaats', 'eBay', 'Coolblue'
    url TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT,
    FOREIGN KEY (lot_id) REFERENCES lots (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_reference_prices_lot_id ON reference_prices (lot_id);

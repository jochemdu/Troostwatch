-- Migration: Add brand column to lots and create bid_history table
-- Schema version: 2
-- Date: 2025-11-27

-- Add brand column to lots table for storing manufacturer/brand information
-- SQLite doesn't support IF NOT EXISTS for ALTER TABLE, so we check via pragma
-- This migration is safe to skip if the column already exists (handled by SchemaMigrator)

-- Create bid_history table to store historical bids on lots
CREATE TABLE IF NOT EXISTS bid_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lot_id INTEGER NOT NULL,
    bidder_label TEXT NOT NULL,
    amount_eur REAL NOT NULL,
    bid_time TEXT,
    FOREIGN KEY (lot_id) REFERENCES lots (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_bid_history_lot_id ON bid_history (lot_id);

-- Migration 0001: Add missing lots columns used by upserts
-- This migration is idempotent when guarded by a migrations table.

ALTER TABLE lots ADD COLUMN IF NOT EXISTS status TEXT;
ALTER TABLE lots ADD COLUMN IF NOT EXISTS opens_at TEXT;
ALTER TABLE lots ADD COLUMN IF NOT EXISTS closing_time_current TEXT;
ALTER TABLE lots ADD COLUMN IF NOT EXISTS closing_time_original TEXT;
ALTER TABLE lots ADD COLUMN IF NOT EXISTS bid_count INTEGER;
ALTER TABLE lots ADD COLUMN IF NOT EXISTS opening_bid_eur REAL;
ALTER TABLE lots ADD COLUMN IF NOT EXISTS current_bid_eur REAL;
ALTER TABLE lots ADD COLUMN IF NOT EXISTS current_bidder_label TEXT;
ALTER TABLE lots ADD COLUMN IF NOT EXISTS current_bid_buyer_id INTEGER;
ALTER TABLE lots ADD COLUMN IF NOT EXISTS buyer_fee_percent REAL;
ALTER TABLE lots ADD COLUMN IF NOT EXISTS buyer_fee_vat_percent REAL;
ALTER TABLE lots ADD COLUMN IF NOT EXISTS vat_percent REAL;
ALTER TABLE lots ADD COLUMN IF NOT EXISTS awarding_state TEXT;
ALTER TABLE lots ADD COLUMN IF NOT EXISTS total_example_price_eur REAL;
ALTER TABLE lots ADD COLUMN IF NOT EXISTS location_city TEXT;
ALTER TABLE lots ADD COLUMN IF NOT EXISTS location_country TEXT;
ALTER TABLE lots ADD COLUMN IF NOT EXISTS seller_allocation_note TEXT;

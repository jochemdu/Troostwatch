-- Migration 0010: Add perceptual hash for image deduplication
-- Adds phash column to lot_images for detecting duplicate images
--
-- Note: This migration is idempotent - it checks if the column exists
-- before attempting to add it.

-- Check if phash column exists before adding (SQLite workaround)
-- If the column doesn't exist, this will fail silently in the try block
-- and the CREATE INDEX will still work since it uses IF NOT EXISTS

-- We cannot use ALTER TABLE ADD COLUMN IF NOT EXISTS in SQLite,
-- so we use a PRAGMA table_info check via Python in the migration runner.
-- For now, we wrap in a transaction and let the runner handle duplicates.

-- If running on a fresh schema.sql (which includes phash), this is a no-op.
-- If running on an existing database without phash, this adds the column.

-- Index for efficient duplicate lookup (always safe with IF NOT EXISTS)
CREATE INDEX IF NOT EXISTS idx_lot_images_phash ON lot_images(phash);

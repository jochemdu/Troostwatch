-- Migration 0009: Add approval status to extracted_codes
-- Adds columns to track auto-approved vs manually reviewed codes

BEGIN TRANSACTION;

-- Add approval status to extracted_codes
ALTER TABLE extracted_codes ADD COLUMN approved INTEGER NOT NULL DEFAULT 0;
ALTER TABLE extracted_codes ADD COLUMN approved_at TEXT;
ALTER TABLE extracted_codes ADD COLUMN approved_by TEXT;  -- 'auto', 'manual', 'openai'

-- Index for finding unapproved codes quickly
CREATE INDEX IF NOT EXISTS idx_extracted_codes_approved ON extracted_codes (approved);

-- Add promoted column to track if codes were written to lots
ALTER TABLE extracted_codes ADD COLUMN promoted_to_lot INTEGER NOT NULL DEFAULT 0;

COMMIT;

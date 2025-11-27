-- Migration 0007: Add release_date and category to specs and templates
-- These fields allow tracking when a product was released and its category/type
--
-- Note: These columns are now defined in schema.sql for new databases.
-- This migration is kept for backwards compatibility with existing databases.
-- SQLite doesn't support IF NOT EXISTS for ALTER TABLE ADD COLUMN,
-- so we only create the indexes which are safe with IF NOT EXISTS.

-- Create indexes for category filtering (these are safe with IF NOT EXISTS)
CREATE INDEX IF NOT EXISTS idx_product_layers_category ON product_layers (category);
CREATE INDEX IF NOT EXISTS idx_spec_templates_category ON spec_templates (category);

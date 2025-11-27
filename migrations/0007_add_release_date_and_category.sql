-- Migration 0007: Add release_date and category to specs and templates
-- These fields allow tracking when a product was released and its category/type
-- Note: SQLite doesn't support IF NOT EXISTS for ALTER TABLE ADD COLUMN
-- The migration system should track applied migrations to prevent re-running.

-- Add columns to product_layers (specs for lots)
-- These will fail if already present; migration system handles this.
ALTER TABLE product_layers ADD COLUMN release_date TEXT;
ALTER TABLE product_layers ADD COLUMN category TEXT;

-- Add columns to spec_templates
ALTER TABLE spec_templates ADD COLUMN release_date TEXT;
ALTER TABLE spec_templates ADD COLUMN category TEXT;

-- Create index for category filtering (these are safe with IF NOT EXISTS)
CREATE INDEX IF NOT EXISTS idx_product_layers_category ON product_layers (category);
CREATE INDEX IF NOT EXISTS idx_spec_templates_category ON spec_templates (category);

-- Migration 0006: Add EAN codes and reusable spec templates
-- - EAN code for lots (barcode/product identification)
-- - EAN and price for specifications
-- - Shared spec templates that can be linked to multiple lots
--
-- Note: These columns and tables are now defined in schema.sql for new databases.
-- This migration is kept for backwards compatibility with existing databases.
-- SQLite doesn't support IF NOT EXISTS for ALTER TABLE, so we use a workaround.

-- Create spec_templates table for reusable specifications (safe with IF NOT EXISTS)
CREATE TABLE IF NOT EXISTS spec_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_id INTEGER,
    title TEXT NOT NULL,
    value TEXT,
    ean TEXT,
    price_eur REAL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT,
    FOREIGN KEY (parent_id) REFERENCES spec_templates (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_spec_templates_parent_id ON spec_templates (parent_id);
CREATE INDEX IF NOT EXISTS idx_spec_templates_ean ON spec_templates (ean);

-- Note: ALTER TABLE ADD COLUMN statements are removed because:
-- 1. New databases already have these columns in schema.sql
-- 2. SQLite ALTER TABLE fails if column exists
-- 3. Old databases should be migrated via a separate data migration process
CREATE INDEX IF NOT EXISTS idx_product_layers_template_id ON product_layers (template_id);

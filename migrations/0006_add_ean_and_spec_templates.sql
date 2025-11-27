-- Migration 0006: Add EAN codes and reusable spec templates
-- - EAN code for lots (barcode/product identification)
-- - EAN and price for specifications
-- - Shared spec templates that can be linked to multiple lots

-- Add EAN to lots table
ALTER TABLE lots ADD COLUMN ean TEXT;

-- Add EAN and price to product_layers (specs)
ALTER TABLE product_layers ADD COLUMN ean TEXT;
ALTER TABLE product_layers ADD COLUMN price_eur REAL;

-- Create spec_templates table for reusable specifications
-- These can be linked to multiple lots via product_layers.template_id
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

-- Add template_id to product_layers to link to reusable templates
ALTER TABLE product_layers ADD COLUMN template_id INTEGER REFERENCES spec_templates(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_product_layers_template_id ON product_layers (template_id);

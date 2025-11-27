-- Migration 0005: Add parent_id to product_layers for hierarchical specs
-- A lot can have components (e.g., Computer) which have subcomponents (e.g., GPU, CPU)

ALTER TABLE product_layers ADD COLUMN parent_id INTEGER REFERENCES product_layers(id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS idx_product_layers_parent_id ON product_layers (parent_id);

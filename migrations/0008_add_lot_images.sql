-- Migration 0008: Add lot_images, extracted_codes, and ocr_token_data tables
-- for image analysis pipeline with ML training support.
--
-- Status values for download_status: 'pending', 'downloaded', 'failed'
-- Status values for analysis_status: 'pending', 'analyzed', 'needs_review', 'failed'

BEGIN TRANSACTION;

-- Table for storing lot image URLs and local paths
CREATE TABLE IF NOT EXISTS lot_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lot_id INTEGER NOT NULL,
    url TEXT NOT NULL,
    local_path TEXT,
    position INTEGER NOT NULL DEFAULT 0,
    download_status TEXT NOT NULL DEFAULT 'pending',
    analysis_status TEXT NOT NULL DEFAULT 'pending',
    analysis_backend TEXT,
    analyzed_at TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT,
    FOREIGN KEY (lot_id) REFERENCES lots (id) ON DELETE CASCADE,
    UNIQUE (lot_id, url)
);

CREATE INDEX IF NOT EXISTS idx_lot_images_lot_id ON lot_images (lot_id);
CREATE INDEX IF NOT EXISTS idx_lot_images_download_status ON lot_images (download_status);
CREATE INDEX IF NOT EXISTS idx_lot_images_analysis_status ON lot_images (analysis_status);

-- Table for storing extracted product codes from images
CREATE TABLE IF NOT EXISTS extracted_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lot_image_id INTEGER NOT NULL,
    code_type TEXT NOT NULL,  -- 'ean', 'serial_number', 'model_number', 'product_code', 'mac', 'uuid', 'other'
    value TEXT NOT NULL,
    confidence TEXT NOT NULL DEFAULT 'medium',  -- 'high', 'medium', 'low'
    context TEXT,  -- where on image this was found
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (lot_image_id) REFERENCES lot_images (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_extracted_codes_lot_image_id ON extracted_codes (lot_image_id);
CREATE INDEX IF NOT EXISTS idx_extracted_codes_code_type ON extracted_codes (code_type);
CREATE INDEX IF NOT EXISTS idx_extracted_codes_value ON extracted_codes (value);

-- Table for storing raw OCR token data for ML training
CREATE TABLE IF NOT EXISTS ocr_token_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lot_image_id INTEGER NOT NULL UNIQUE,
    tokens_json TEXT NOT NULL,  -- JSON blob with pytesseract.image_to_data() output
    token_count INTEGER NOT NULL DEFAULT 0,
    has_labels INTEGER NOT NULL DEFAULT 0,  -- 1 if manually labeled for training
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (lot_image_id) REFERENCES lot_images (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_ocr_token_data_lot_image_id ON ocr_token_data (lot_image_id);
CREATE INDEX IF NOT EXISTS idx_ocr_token_data_has_labels ON ocr_token_data (has_labels);

COMMIT;

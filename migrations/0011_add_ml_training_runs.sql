-- Migration: Add ml_training_runs table for ML training run tracking
-- Schema version: 9

BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS ml_training_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL, -- 'pending', 'running', 'completed', 'failed'
    model_path TEXT,      -- Path to saved model file
    metrics_json TEXT,    -- JSON blob with training metrics (accuracy, loss, etc.)
    notes TEXT,
    created_by TEXT,      -- User or process that triggered the run
    training_data_filter TEXT, -- Description of training data selection/filter
    error_message TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_ml_training_runs_status ON ml_training_runs (status);
CREATE INDEX IF NOT EXISTS idx_ml_training_runs_started_at ON ml_training_runs (started_at);
CREATE INDEX IF NOT EXISTS idx_ml_training_runs_finished_at ON ml_training_runs (finished_at);

COMMIT;

ALTER TABLE predictions
ADD COLUMN IF NOT EXISTS created_by VARCHAR(100);

CREATE INDEX IF NOT EXISTS idx_prediction_created_by ON predictions(created_by);

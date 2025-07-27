-- Add missing columns to races table
ALTER TABLE races ADD COLUMN IF NOT EXISTS horse_count INTEGER DEFAULT 0;
ALTER TABLE races ADD COLUMN IF NOT EXISTS is_completed BOOLEAN DEFAULT FALSE;
ALTER TABLE races ADD COLUMN IF NOT EXISTS error_message TEXT;

-- Add race_count column to collection_jobs
ALTER TABLE collection_jobs ADD COLUMN IF NOT EXISTS race_count INTEGER DEFAULT 0;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_races_is_completed ON races(is_completed);
CREATE INDEX IF NOT EXISTS idx_cache_expires_at ON horse_cache(expires_at);
CREATE INDEX IF NOT EXISTS idx_cache_expires_at ON jockey_cache(expires_at);
CREATE INDEX IF NOT EXISTS idx_cache_expires_at ON trainer_cache(expires_at);
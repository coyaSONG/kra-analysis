-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enum for race status
CREATE TYPE race_status AS ENUM ('pending', 'collected', 'enriched', 'failed');

-- Races table
CREATE TABLE IF NOT EXISTS races (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date VARCHAR(8) NOT NULL,
    meet INTEGER NOT NULL CHECK (meet IN (1, 2, 3)),
    race_no INTEGER NOT NULL CHECK (race_no >= 1 AND race_no <= 20),
    race_name TEXT,
    distance INTEGER,
    grade VARCHAR(10),
    track_condition VARCHAR(20),
    weather VARCHAR(20),
    status race_status DEFAULT 'pending',
    raw_data JSONB,
    enriched_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Unique constraint to prevent duplicate races
    CONSTRAINT unique_race UNIQUE (date, meet, race_no)
);

-- Create indexes for common queries
CREATE INDEX idx_races_date ON races(date);
CREATE INDEX idx_races_date_meet ON races(date, meet);
CREATE INDEX idx_races_status ON races(status);

-- Race results table
CREATE TABLE IF NOT EXISTS race_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    race_id UUID NOT NULL REFERENCES races(id) ON DELETE CASCADE,
    winner INTEGER NOT NULL,
    second INTEGER NOT NULL,
    third INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Unique constraint to prevent duplicate results
    CONSTRAINT unique_race_result UNIQUE (race_id)
);

-- Predictions table
CREATE TABLE IF NOT EXISTS predictions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    race_id UUID NOT NULL REFERENCES races(id) ON DELETE CASCADE,
    prompt_version VARCHAR(50) NOT NULL,
    predicted_winner INTEGER NOT NULL,
    predicted_second INTEGER NOT NULL,
    predicted_third INTEGER NOT NULL,
    confidence FLOAT,
    reasoning TEXT,
    is_correct BOOLEAN,
    correct_count INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Index for performance queries
    INDEX idx_predictions_race_id (race_id),
    INDEX idx_predictions_prompt_version (prompt_version),
    INDEX idx_predictions_created_at (created_at)
);

-- Collection jobs table
CREATE TABLE IF NOT EXISTS collection_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date VARCHAR(8) NOT NULL,
    meet INTEGER NOT NULL,
    race_no INTEGER,
    status VARCHAR(20) DEFAULT 'queued',
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Horse cache table
CREATE TABLE IF NOT EXISTS horse_cache (
    horse_no VARCHAR(20) PRIMARY KEY,
    data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP + INTERVAL '7 days'
);

-- Jockey cache table  
CREATE TABLE IF NOT EXISTS jockey_cache (
    jockey_no VARCHAR(20) PRIMARY KEY,
    data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP + INTERVAL '7 days'
);

-- Trainer cache table
CREATE TABLE IF NOT EXISTS trainer_cache (
    trainer_no VARCHAR(20) PRIMARY KEY,
    data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP + INTERVAL '7 days'
);

-- Prompt versions table
CREATE TABLE IF NOT EXISTS prompt_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    version VARCHAR(50) UNIQUE NOT NULL,
    content TEXT NOT NULL,
    parent_version VARCHAR(50),
    performance_metrics JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Performance analysis table
CREATE TABLE IF NOT EXISTS performance_analysis (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prompt_version VARCHAR(50) NOT NULL,
    analysis_date DATE NOT NULL,
    total_races INTEGER NOT NULL,
    successful_predictions INTEGER NOT NULL,
    success_rate FLOAT NOT NULL,
    insights JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for races table
CREATE TRIGGER update_races_updated_at BEFORE UPDATE ON races
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Row Level Security (RLS)
ALTER TABLE races ENABLE ROW LEVEL SECURITY;
ALTER TABLE race_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE predictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE collection_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE horse_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE jockey_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE trainer_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE prompt_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE performance_analysis ENABLE ROW LEVEL SECURITY;

-- Create policies (adjust based on your authentication strategy)
-- For now, allowing all operations for authenticated users
CREATE POLICY "Enable all for authenticated users" ON races
    FOR ALL USING (true);

CREATE POLICY "Enable all for authenticated users" ON race_results
    FOR ALL USING (true);

CREATE POLICY "Enable all for authenticated users" ON predictions
    FOR ALL USING (true);

-- Add more specific policies as needed
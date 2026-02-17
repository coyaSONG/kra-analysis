-- KRA Analysis Unified Schema
-- Aligned with SQLAlchemy models in apps/api/models/database_models.py
-- Supabase Best Practices: GIN indexes for JSONB, BRIN for time-series, proper RLS

-- =============================================================================
-- Extensions
-- =============================================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- Custom Types
-- =============================================================================
DO $$ BEGIN
    CREATE TYPE data_status AS ENUM ('pending', 'collected', 'enriched', 'failed');
EXCEPTION WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE job_type AS ENUM ('collection', 'enrichment', 'analysis', 'prediction', 'improvement', 'batch');
EXCEPTION WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE job_status AS ENUM ('pending', 'queued', 'processing', 'running', 'completed', 'failed', 'cancelled', 'retrying');
EXCEPTION WHEN duplicate_object THEN null;
END $$;

-- =============================================================================
-- Tables
-- =============================================================================

-- Races table
CREATE TABLE IF NOT EXISTS races (
    race_id VARCHAR(50) PRIMARY KEY,
    date VARCHAR(8) NOT NULL,
    meet INTEGER NOT NULL CHECK (meet IN (1, 2, 3)),
    race_number INTEGER NOT NULL,
    race_name VARCHAR(200),
    distance INTEGER,
    track VARCHAR(50),
    weather VARCHAR(50),

    -- Status fields
    collection_status data_status DEFAULT 'pending',
    enrichment_status data_status DEFAULT 'pending',
    result_status data_status DEFAULT 'pending',

    -- Data (JSONB for Supabase compatibility)
    basic_data JSONB,
    raw_data JSONB,
    enriched_data JSONB,
    result_data JSONB,

    -- Timestamps
    collected_at TIMESTAMPTZ,
    enriched_at TIMESTAMPTZ,
    result_collected_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    -- Metadata
    data_quality_score FLOAT DEFAULT 0.0,
    warnings JSONB DEFAULT '[]'::jsonb,
    horse_count INTEGER DEFAULT 0,

    CONSTRAINT unique_race UNIQUE (date, meet, race_number)
);

-- B-tree indexes
CREATE INDEX IF NOT EXISTS idx_races_date ON races(date);
CREATE INDEX IF NOT EXISTS idx_race_date_meet ON races(date, meet);
CREATE INDEX IF NOT EXISTS idx_race_status ON races(collection_status, enrichment_status);

-- GIN indexes for JSONB queries
CREATE INDEX IF NOT EXISTS idx_races_enriched_data ON races USING gin(enriched_data);
CREATE INDEX IF NOT EXISTS idx_races_result_data ON races USING gin(result_data);

-- BRIN index for time-series (10x smaller than B-tree)
CREATE INDEX IF NOT EXISTS idx_races_created_at ON races USING brin(created_at);


-- Predictions table
CREATE TABLE IF NOT EXISTS predictions (
    prediction_id VARCHAR(100) PRIMARY KEY,
    race_id VARCHAR(50) NOT NULL REFERENCES races(race_id) ON DELETE CASCADE,
    prompt_id VARCHAR(50) NOT NULL,
    prompt_version VARCHAR(20),
    predicted_positions JSONB,
    confidence INTEGER,
    reasoning TEXT,
    actual_result JSONB,
    accuracy_score FLOAT,
    correct_count INTEGER,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    execution_time_ms INTEGER,
    model_version VARCHAR(50)
);

CREATE INDEX IF NOT EXISTS idx_prediction_race_id ON predictions(race_id);
CREATE INDEX IF NOT EXISTS idx_prediction_prompt ON predictions(prompt_id, created_at);
CREATE INDEX IF NOT EXISTS idx_prediction_accuracy ON predictions(accuracy_score, created_at);


-- Jobs table
CREATE TABLE IF NOT EXISTS jobs (
    job_id VARCHAR(100) PRIMARY KEY,
    type job_type NOT NULL,
    status job_status DEFAULT 'queued',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    progress INTEGER DEFAULT 0,
    current_step VARCHAR(200),
    total_steps INTEGER,
    result JSONB,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    parameters JSONB,
    created_by VARCHAR(100),
    tags JSONB DEFAULT '[]'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_job_created_status ON jobs(created_at, status);
CREATE INDEX IF NOT EXISTS idx_job_type_status ON jobs(type, status);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs USING brin(created_at);


-- Job logs table
CREATE TABLE IF NOT EXISTS job_logs (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(100) NOT NULL REFERENCES jobs(job_id),
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    level VARCHAR(20),
    message TEXT,
    log_metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_job_logs_job_id ON job_logs(job_id);


-- API keys table
CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    rate_limit INTEGER DEFAULT 100,
    daily_limit INTEGER DEFAULT 10000,
    permissions JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    total_requests INTEGER DEFAULT 0,
    today_requests INTEGER DEFAULT 0,
    created_by VARCHAR(100),
    key_metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_api_keys_key ON api_keys(key);
CREATE INDEX IF NOT EXISTS idx_api_keys_created_by ON api_keys(created_by);


-- Prompt templates table
CREATE TABLE IF NOT EXISTS prompt_templates (
    id SERIAL PRIMARY KEY,
    prompt_id VARCHAR(50) UNIQUE NOT NULL,
    version VARCHAR(20) NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    template_content TEXT NOT NULL,
    total_uses INTEGER DEFAULT 0,
    success_rate FLOAT DEFAULT 0.0,
    avg_accuracy FLOAT DEFAULT 0.0,
    is_active BOOLEAN DEFAULT TRUE,
    is_baseline BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    tags JSONB DEFAULT '[]'::jsonb,
    template_metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_prompt_templates_prompt_id ON prompt_templates(prompt_id);


-- =============================================================================
-- Triggers
-- =============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_races_updated_at ON races;
CREATE TRIGGER update_races_updated_at
    BEFORE UPDATE ON races
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_prompt_templates_updated_at ON prompt_templates;
CREATE TRIGGER update_prompt_templates_updated_at
    BEFORE UPDATE ON prompt_templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- =============================================================================
-- Row Level Security
-- =============================================================================

ALTER TABLE races ENABLE ROW LEVEL SECURITY;
ALTER TABLE predictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE prompt_templates ENABLE ROW LEVEL SECURITY;

-- Service role: full access (API server uses service role key)
CREATE POLICY "Service role full access" ON races FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON predictions FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON jobs FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON job_logs FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON api_keys FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON prompt_templates FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Authenticated: read-only access (for dashboard, if needed)
CREATE POLICY "Authenticated read access" ON races FOR SELECT TO authenticated USING (true);
CREATE POLICY "Authenticated read access" ON predictions FOR SELECT TO authenticated USING (true);
CREATE POLICY "Authenticated read access" ON jobs FOR SELECT TO authenticated USING (true);
CREATE POLICY "Authenticated read access" ON prompt_templates FOR SELECT TO authenticated USING (true);

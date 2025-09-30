-- 003: SQLAlchemy 모델과 스키마 동기화
-- SQLAlchemy 모델이 사용하는 구조에 맞게 races 테이블 수정

-- Step 1: 기존 races 테이블 백업 (데이터가 있는 경우를 대비)
-- DO $$
-- BEGIN
--     IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'races') THEN
--         CREATE TABLE IF NOT EXISTS races_backup AS SELECT * FROM races;
--     END IF;
-- END $$;

-- Step 2: 새로운 data_status enum 생성 (race_status와 다름)
DO $$ BEGIN
    CREATE TYPE data_status AS ENUM ('pending', 'collected', 'enriched', 'failed');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Step 3: races 테이블 재구성
-- 기존 테이블을 삭제하고 SQLAlchemy 모델과 일치하는 새 테이블 생성
DROP TABLE IF EXISTS predictions CASCADE;
DROP TABLE IF EXISTS race_results CASCADE;
DROP TABLE IF EXISTS races CASCADE;
DROP TYPE IF EXISTS race_status CASCADE;

-- Races table (SQLAlchemy 모델 기준)
CREATE TABLE races (
    race_id VARCHAR(50) PRIMARY KEY,  -- SQLAlchemy uses String(50)
    date VARCHAR(8) NOT NULL,
    meet INTEGER NOT NULL CHECK (meet IN (1, 2, 3)),
    race_number INTEGER NOT NULL,  -- SQLAlchemy uses race_number not race_no
    race_name VARCHAR(200),
    distance INTEGER,
    track VARCHAR(50),
    weather VARCHAR(50),

    -- 통합된 상태 필드 (3개)
    collection_status data_status DEFAULT 'pending',
    enrichment_status data_status DEFAULT 'pending',
    result_status data_status DEFAULT 'pending',

    -- 데이터 필드
    basic_data JSONB,
    raw_data JSONB,
    enriched_data JSONB,
    result_data JSONB,

    -- 타임스탬프
    collected_at TIMESTAMP WITH TIME ZONE,
    enriched_at TIMESTAMP WITH TIME ZONE,
    result_collected_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- 메타데이터
    data_quality_score FLOAT DEFAULT 0.0,
    warnings JSONB DEFAULT '[]'::jsonb,
    horse_count INTEGER DEFAULT 0,

    -- Unique constraint
    CONSTRAINT unique_race UNIQUE (date, meet, race_number)
);

-- Indexes
CREATE INDEX idx_races_date ON races(date);
CREATE INDEX idx_race_date_meet ON races(date, meet);
CREATE INDEX idx_race_status ON races(collection_status, enrichment_status);

-- Race results table
CREATE TABLE race_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    race_id VARCHAR(50) NOT NULL REFERENCES races(race_id) ON DELETE CASCADE,
    winner INTEGER NOT NULL,
    second INTEGER NOT NULL,
    third INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_race_result UNIQUE (race_id)
);

-- Predictions table (SQLAlchemy 모델 기준)
CREATE TABLE predictions (
    prediction_id VARCHAR(100) PRIMARY KEY,  -- SQLAlchemy uses String(100)
    race_id VARCHAR(50) NOT NULL REFERENCES races(race_id) ON DELETE CASCADE,

    -- 예측 정보
    prompt_id VARCHAR(50) NOT NULL,
    prompt_version VARCHAR(20),

    -- 예측 결과
    predicted_positions JSONB,  -- [1st, 2nd, 3rd]
    confidence INTEGER,
    reasoning TEXT,

    -- 평가
    actual_result JSONB,
    accuracy_score FLOAT,
    correct_count INTEGER,

    -- 메타데이터
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    execution_time_ms INTEGER,
    model_version VARCHAR(50)
);

-- Indexes for predictions
CREATE INDEX idx_prediction_race_id ON predictions(race_id);
CREATE INDEX idx_prediction_prompt ON predictions(prompt_id, created_at);
CREATE INDEX idx_prediction_accuracy ON predictions(accuracy_score, created_at);

-- Jobs table (SQLAlchemy 모델 기준)
DO $$ BEGIN
    CREATE TYPE job_type AS ENUM ('collection', 'enrichment', 'analysis', 'prediction', 'improvement', 'batch');
    CREATE TYPE job_status AS ENUM ('pending', 'queued', 'processing', 'running', 'completed', 'failed', 'cancelled', 'retrying');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

CREATE TABLE IF NOT EXISTS jobs (
    job_id VARCHAR(100) PRIMARY KEY,
    type job_type NOT NULL,
    status job_status DEFAULT 'queued',

    -- 시간 정보
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,

    -- 진행 상황
    progress INTEGER DEFAULT 0,
    current_step VARCHAR(200),
    total_steps INTEGER,

    -- 결과 및 에러
    result JSONB,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,

    -- 메타데이터
    parameters JSONB,
    created_by VARCHAR(100),
    tags JSONB DEFAULT '[]'::jsonb
);

CREATE INDEX idx_job_created_status ON jobs(created_at, status);
CREATE INDEX idx_job_type_status ON jobs(type, status);

-- Job logs table
CREATE TABLE IF NOT EXISTS job_logs (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(100) NOT NULL REFERENCES jobs(job_id),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    level VARCHAR(20),
    message TEXT,
    log_metadata JSONB
);

CREATE INDEX idx_job_logs_job_id ON job_logs(job_id);

-- API Keys table
CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,

    -- 사용량 제한
    rate_limit INTEGER DEFAULT 100,
    daily_limit INTEGER DEFAULT 10000,

    -- 권한
    permissions JSONB DEFAULT '[]'::jsonb,

    -- 타임스탬프
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,

    -- 사용량 추적
    total_requests INTEGER DEFAULT 0,
    today_requests INTEGER DEFAULT 0,

    -- 메타데이터
    created_by VARCHAR(100),
    key_metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_api_keys_key ON api_keys(key);
CREATE INDEX idx_api_keys_created_by ON api_keys(created_by);

-- Prompt templates table
CREATE TABLE IF NOT EXISTS prompt_templates (
    id SERIAL PRIMARY KEY,
    prompt_id VARCHAR(50) UNIQUE NOT NULL,
    version VARCHAR(20) NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,

    -- 내용
    template_content TEXT NOT NULL,

    -- 성능 지표
    total_uses INTEGER DEFAULT 0,
    success_rate FLOAT DEFAULT 0.0,
    avg_accuracy FLOAT DEFAULT 0.0,

    -- 상태
    is_active BOOLEAN DEFAULT TRUE,
    is_baseline BOOLEAN DEFAULT FALSE,

    -- 타임스탬프
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- 메타데이터
    tags JSONB DEFAULT '[]'::jsonb,
    template_metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_prompt_templates_prompt_id ON prompt_templates(prompt_id);

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_races_updated_at BEFORE UPDATE ON races
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_prompt_templates_updated_at BEFORE UPDATE ON prompt_templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- RLS (Row Level Security)
ALTER TABLE races ENABLE ROW LEVEL SECURITY;
ALTER TABLE race_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE predictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE prompt_templates ENABLE ROW LEVEL SECURITY;

-- Policies (Allow all for now - adjust based on authentication)
CREATE POLICY "Enable all for authenticated users" ON races FOR ALL USING (true);
CREATE POLICY "Enable all for authenticated users" ON race_results FOR ALL USING (true);
CREATE POLICY "Enable all for authenticated users" ON predictions FOR ALL USING (true);
CREATE POLICY "Enable all for authenticated users" ON jobs FOR ALL USING (true);
CREATE POLICY "Enable all for authenticated users" ON job_logs FOR ALL USING (true);
CREATE POLICY "Enable all for authenticated users" ON api_keys FOR ALL USING (true);
CREATE POLICY "Enable all for authenticated users" ON prompt_templates FOR ALL USING (true);
# Supabase Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate from unconfigured local PostgreSQL to Supabase cloud with a unified, best-practices schema.

**Architecture:** The API app (`apps/api`) connects to Supabase via asyncpg + SQLAlchemy. The collector app is unchanged. Old inconsistent migrations are replaced with a single unified schema. Local docker-compose is preserved as fallback.

**Tech Stack:** PostgreSQL 15 (Supabase), SQLAlchemy 2.0+, asyncpg, FastAPI, pgbouncer (Supabase pooler)

**Design doc:** `docs/plans/2026-02-18-supabase-migration-design.md`

---

### Task 1: Create Supabase Project (Manual)

**This is a manual step the user performs in the Supabase dashboard.**

**Step 1: Create project**

Go to https://supabase.com/dashboard and create a new project.
- Region: Choose closest (e.g., `ap-northeast-2` for Korea)
- Database password: Save securely

**Step 2: Get credentials**

From Project Settings > API, collect:
- `Project URL` → `SUPABASE_URL`
- `anon public key` → `SUPABASE_ANON_KEY`
- `service_role key` → `SUPABASE_SERVICE_ROLE_KEY`

From Project Settings > Database > Connection string (URI), get the **Transaction pooler** string:
```
postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
```

Convert to asyncpg format by adding `+asyncpg`:
```
postgresql+asyncpg://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
```

**Step 3: Verify collected values**

You should now have 4 values:
- `DATABASE_URL` (asyncpg transaction pooler string)
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`

---

### Task 2: Write Unified Migration SQL

**Files:**
- Create: `apps/api/migrations/001_unified_schema.sql`
- Delete: `apps/api/migrations/002_add_missing_columns.sql`
- Delete: `apps/api/migrations/003_align_with_sqlalchemy_models.sql`

**Step 1: Replace old 001 migration with unified schema**

Write `apps/api/migrations/001_unified_schema.sql` with this content.
The schema matches `apps/api/models/database_models.py` exactly, with Supabase best practices added.

```sql
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
```

**Step 2: Delete old migration files**

Delete these files:
- `apps/api/migrations/002_add_missing_columns.sql`
- `apps/api/migrations/003_align_with_sqlalchemy_models.sql`

**Step 3: Commit**

```bash
git add apps/api/migrations/
git commit -m "refactor(db): unify migration files with Supabase best practices"
```

---

### Task 3: Apply Migration to Supabase

**This step requires the user to have completed Task 1.**

**Step 1: Apply via Supabase SQL Editor**

Go to Supabase Dashboard > SQL Editor. Paste the contents of `apps/api/migrations/001_unified_schema.sql` and run.

**Step 2: Verify tables were created**

In SQL Editor, run:
```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' ORDER BY table_name;
```

Expected: `api_keys`, `job_logs`, `jobs`, `predictions`, `prompt_templates`, `races`

**Step 3: Verify indexes were created**

```sql
SELECT indexname, tablename FROM pg_indexes
WHERE schemaname = 'public' ORDER BY tablename, indexname;
```

Expected: All indexes from the migration (idx_races_date, idx_race_date_meet, idx_races_enriched_data, etc.)

**Step 4: Verify RLS policies**

```sql
SELECT tablename, policyname FROM pg_policies
WHERE schemaname = 'public' ORDER BY tablename;
```

Expected: "Service role full access" and "Authenticated read access" policies on each table.

---

### Task 4: Update Environment Configuration

**Files:**
- Modify: `apps/api/.env`
- Modify: `apps/api/config.py:28-30` (database_url default)

**Step 1: Update `.env` with Supabase credentials**

Edit `apps/api/.env` to add Supabase connection details. Replace placeholder values with actual credentials from Task 1.

```env
# FastAPI API server environment

# Core
ENVIRONMENT=development
PORT=8001
SECRET_KEY=changeme-secret-key

# Database (Supabase transaction pooler)
DATABASE_URL=postgresql+asyncpg://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres

# Supabase
SUPABASE_URL=https://[ref].supabase.co
SUPABASE_ANON_KEY=[your-anon-key]
SUPABASE_SERVICE_ROLE_KEY=[your-service-role-key]

# Redis / Cache
REDIS_URL=redis://localhost:6379/0

# Logging
LOG_LEVEL=info
```

**Step 2: Update config.py default to require DATABASE_URL**

In `apps/api/config.py`, change the `database_url` default to signal it must come from `.env`:

```python
    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://kra_user:kra_password@localhost:5432/kra_analysis",
        description="Database connection URL. Set via DATABASE_URL env var for Supabase.",
    )
```

This is a minimal change - keep the localhost default so docker-compose still works, but add the Field description as documentation.

**Step 3: Run existing tests to verify nothing breaks**

```bash
cd apps/api && uv run pytest tests/ -x -q
```

Expected: All tests pass (tests use SQLite in-memory, independent of DATABASE_URL).

**Step 4: Commit**

```bash
git add apps/api/.env apps/api/config.py
git commit -m "feat(config): add Supabase credentials to .env"
```

> **IMPORTANT:** `.env` is in `.gitignore`. If it is NOT, do NOT commit it. Only commit `config.py` changes. Verify with `git status` before committing.

---

### Task 5: Verify Supabase Connection

**Step 1: Start the API server**

```bash
cd apps/api && uv run python3 main_v2.py
```

Expected: Server starts, logs show "Database initialized successfully".

**Step 2: Test health check endpoint**

```bash
curl http://localhost:8001/health/detailed
```

Expected:
```json
{
  "status": "healthy" or "degraded",
  "database": "healthy",
  "redis": "healthy" or "unhealthy",
  ...
}
```

The critical check is `"database": "healthy"`. Redis may be unhealthy if not running locally.

**Step 3: Test a write operation via API**

Create a test collection job:
```bash
curl -X POST http://localhost:8001/api/v2/collection/races/20250101/1 \
  -H "X-API-Key: test-api-key-123456789"
```

Then check Supabase Dashboard > Table Editor > `races` to verify data was written.

**Step 4: Verify via Supabase SQL Editor**

```sql
SELECT count(*) FROM races;
SELECT count(*) FROM jobs;
```

If any rows exist, the write path is working.

---

### Task 6: Final Verification and Cleanup

**Step 1: Run full test suite**

```bash
cd apps/api && uv run pytest tests/ -v --tb=short
```

Expected: All tests pass. Tests use SQLite in-memory so they are unaffected by the Supabase migration.

**Step 2: Verify docker-compose still works as local fallback**

```bash
cd apps/api && docker compose up postgres -d
```

Temporarily set `DATABASE_URL=postgresql+asyncpg://kra_user:kra_password@localhost:5432/kra_analysis` and verify API starts.

Then shut down: `docker compose down`

**Step 3: Final commit**

If any cleanup was needed during verification:

```bash
git add -A
git commit -m "chore: finalize Supabase migration verification"
```

---

## Success Criteria Checklist

- [ ] Supabase project created with credentials collected
- [ ] Unified migration SQL applied (6 tables, GIN/BRIN indexes, RLS policies)
- [ ] Old migration files (002, 003) deleted
- [ ] `.env` updated with Supabase connection string
- [ ] API server connects to Supabase (`/health/detailed` returns `database: healthy`)
- [ ] Write operations persist to Supabase (visible in dashboard)
- [ ] All existing tests pass (`uv run pytest tests/ -v`)
- [ ] Docker-compose local fallback still works

# Supabase Migration Design

Date: 2026-02-18

## Overview

Migrate from local PostgreSQL (not yet provisioned) to Supabase cloud with optimized schema and best practices.

## Current State

- `DATABASE_URL` points to `localhost:5432/kra` (Docker container not running)
- No data exists in local DB or `data/` folder
- 3 migration files with schema inconsistencies (race_no vs race_number, collection_jobs vs jobs)
- SQLAlchemy models are the source of truth (most recent)
- Collector app: independent, no DB connection, Redis/file cache only

## Target State

- Supabase cloud PostgreSQL as primary database
- Unified schema aligned with SQLAlchemy models
- Supabase Best Practices applied (GIN indexes, BRIN indexes, proper RLS)
- Local docker-compose preserved for development fallback

## Schema Design

### Tables (Keep)

| Table | Purpose | Changes |
|-------|---------|---------|
| `races` | Race data with JSONB columns | Unified from 003 migration, add GIN indexes |
| `predictions` | AI prediction results | No changes |
| `jobs` | Job management | No changes (replaces old collection_jobs) |
| `job_logs` | Job execution logs | No changes |
| `api_keys` | API authentication | No changes |
| `prompt_templates` | Prompt version management | No changes |

### Tables (Remove)

| Table | Reason |
|-------|--------|
| `horse_cache` | Collector handles caching via Redis/file |
| `jockey_cache` | Collector handles caching via Redis/file |
| `trainer_cache` | Collector handles caching via Redis/file |
| `race_results` | Consolidated into races.result_data JSONB |
| `performance_analysis` | Can be derived from predictions table |
| `collection_jobs` | Replaced by unified jobs table |
| `prompt_versions` | Replaced by prompt_templates table |

### Indexing Strategy (Supabase Best Practices)

```sql
-- B-tree indexes (equality/range queries)
CREATE INDEX idx_races_date ON races(date);
CREATE INDEX idx_race_date_meet ON races(date, meet);
CREATE INDEX idx_race_status ON races(collection_status, enrichment_status);

-- GIN indexes (JSONB containment queries)
CREATE INDEX idx_races_enriched_data ON races USING gin(enriched_data);
CREATE INDEX idx_races_result_data ON races USING gin(result_data);

-- BRIN indexes (time-series data, 10x smaller than B-tree)
CREATE INDEX idx_races_created_at ON races USING brin(created_at);
CREATE INDEX idx_jobs_created_at ON jobs USING brin(created_at);

-- Prediction composite indexes
CREATE INDEX idx_prediction_prompt ON predictions(prompt_id, created_at);
CREATE INDEX idx_prediction_accuracy ON predictions(accuracy_score, created_at);
```

### RLS Policies

```sql
-- Service role: full access (API server uses service role key)
CREATE POLICY "Service role full access" ON races
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Authenticated: read-only (if needed for dashboard)
CREATE POLICY "Authenticated read access" ON races
  FOR SELECT TO authenticated USING (true);
```

## Infrastructure Changes

### Files to Modify

1. **`apps/api/migrations/001_unified_schema.sql`** - New unified migration replacing all 3
2. **`apps/api/config.py`** - Remove localhost default, require DATABASE_URL from .env
3. **`apps/api/.env`** - Update connection strings to Supabase
4. **`apps/api/models/database_models.py`** - Minimal: ensure JSONB type usage

### Files NOT to Modify

- `apps/collector/` - No changes needed
- `apps/api/infrastructure/database.py` - Already Supabase-compatible
- `apps/api/infrastructure/supabase_client.py` - Already correct
- `apps/api/docker-compose.yml` - Keep for local development

### Environment Variables

```env
# Supabase connection (transaction pooler for pgbouncer compatibility)
DATABASE_URL=postgresql+asyncpg://postgres.[ref]:[pass]@aws-0-[region].pooler.supabase.com:6543/postgres
SUPABASE_URL=https://[ref].supabase.co
SUPABASE_ANON_KEY=[anon-key]
SUPABASE_SERVICE_ROLE_KEY=[service-role-key]
```

## Data Flow (Unchanged)

```
KRA Public API → Collector (cache) → HTTP Response → API App → Supabase DB
```

## Implementation Steps

1. Create Supabase project (manual, via dashboard)
2. Write unified migration SQL
3. Apply migration to Supabase via SQL Editor or CLI
4. Update .env with Supabase credentials
5. Update config.py defaults
6. Remove old migration files, add new unified one
7. Test API connection to Supabase
8. Verify CRUD operations work end-to-end

## Success Criteria

- API app connects to Supabase and all endpoints work
- Race collection → enrichment → prediction pipeline works
- RLS policies properly configured
- GIN/BRIN indexes created and verified
- Local docker-compose still works as fallback

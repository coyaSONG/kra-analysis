-- Runtime database hardening for current SQLAlchemy models and Supabase RLS.

ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS task_id VARCHAR(200);

CREATE INDEX IF NOT EXISTS idx_jobs_task_id
ON jobs(task_id)
WHERE task_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_jobs_created_by_created_at
ON jobs(created_by, created_at DESC)
WHERE created_by IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_races_result_collected_date
ON races(date DESC)
WHERE result_status = 'collected';

ALTER TABLE usage_events ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    DROP POLICY IF EXISTS "Service role full access" ON usage_events;
    CREATE POLICY "Service role full access" ON usage_events
        FOR ALL TO service_role USING (true) WITH CHECK (true);
END $$;

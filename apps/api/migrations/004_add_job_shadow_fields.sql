ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS job_kind_v2 VARCHAR(100);

ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS lifecycle_state_v2 VARCHAR(50);

UPDATE jobs
SET job_kind_v2 = CASE
    WHEN type::text = 'batch' THEN 'batch_collect'
    WHEN type::text = 'enrichment' THEN 'enrichment'
    WHEN type::text = 'analysis' THEN 'analysis'
    WHEN type::text = 'prediction' THEN 'prediction'
    WHEN type::text = 'improvement' THEN 'improvement'
    ELSE type::text
END
WHERE job_kind_v2 IS NULL;

UPDATE jobs
SET lifecycle_state_v2 = CASE
    WHEN status::text = 'running' THEN 'processing'
    WHEN status::text = 'retrying' THEN 'processing'
    ELSE status::text
END
WHERE lifecycle_state_v2 IS NULL;

CREATE INDEX IF NOT EXISTS idx_jobs_job_kind_v2 ON jobs(job_kind_v2);
CREATE INDEX IF NOT EXISTS idx_jobs_lifecycle_state_v2 ON jobs(lifecycle_state_v2);
CREATE INDEX IF NOT EXISTS idx_jobs_job_kind_v2_state_v2 ON jobs(job_kind_v2, lifecycle_state_v2);

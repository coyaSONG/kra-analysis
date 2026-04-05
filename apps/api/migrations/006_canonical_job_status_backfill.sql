UPDATE jobs
SET status = 'processing'
WHERE status::text IN ('running', 'retrying');

UPDATE jobs
SET lifecycle_state_v2 = 'processing'
WHERE status::text = 'processing'
  AND (
    lifecycle_state_v2 IS NULL
    OR lifecycle_state_v2 IN ('running', 'retrying')
  );

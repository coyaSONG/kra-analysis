CREATE TABLE IF NOT EXISTS usage_events (
    id SERIAL PRIMARY KEY,
    principal_id VARCHAR(150) NOT NULL,
    owner_ref VARCHAR(150) NOT NULL,
    credential_id VARCHAR(150),
    action VARCHAR(100) NOT NULL,
    units INTEGER NOT NULL DEFAULT 1,
    outcome VARCHAR(30) NOT NULL,
    status_code INTEGER,
    request_id VARCHAR(100),
    method VARCHAR(16),
    path VARCHAR(255),
    error_detail TEXT,
    event_metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_usage_events_principal_id ON usage_events(principal_id);
CREATE INDEX IF NOT EXISTS idx_usage_events_owner_ref ON usage_events(owner_ref);
CREATE INDEX IF NOT EXISTS idx_usage_events_action ON usage_events(action);
CREATE INDEX IF NOT EXISTS idx_usage_events_outcome ON usage_events(outcome);
CREATE INDEX IF NOT EXISTS idx_usage_events_request_id ON usage_events(request_id);
CREATE INDEX IF NOT EXISTS idx_usage_events_created_at ON usage_events(created_at);

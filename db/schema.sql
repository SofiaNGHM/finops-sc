CREATE TABLE IF NOT EXISTS audit_events (
    id BIGSERIAL PRIMARY KEY,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    action TEXT NOT NULL,
    resource_id TEXT,
    mode TEXT NOT NULL,
    result TEXT NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS cost_scenarios (
    id BIGSERIAL PRIMARY KEY,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    scenario TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    hourly_usd NUMERIC(12, 6) NOT NULL,
    hours NUMERIC(12, 2) NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('estimate', 'aws_actual'))
);

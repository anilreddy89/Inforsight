CREATE TABLE trusted_agent_handoff (
    case_id VARCHAR(128) PRIMARY KEY REFERENCES control_case(case_id),
    case_version BIGINT NOT NULL CHECK (case_version = 0),
    snapshot_id VARCHAR(128) NOT NULL REFERENCES policy_snapshot(snapshot_id),
    event_id VARCHAR(128) NOT NULL UNIQUE,
    handoff_json JSONB NOT NULL,
    created_at_utc TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

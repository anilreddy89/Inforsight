CREATE TABLE agent_review_draft (
    case_id VARCHAR(128) PRIMARY KEY REFERENCES control_case(case_id),
    case_version BIGINT NOT NULL CHECK (case_version >= 0),
    snapshot_id VARCHAR(128) NOT NULL REFERENCES policy_snapshot(snapshot_id),
    idempotency_key VARCHAR(128) NOT NULL,
    request_digest CHAR(64) NOT NULL,
    draft_json JSONB NOT NULL,
    audit_event_id UUID NOT NULL UNIQUE,
    created_at_utc TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX agent_review_draft_snapshot_idx ON agent_review_draft (snapshot_id);

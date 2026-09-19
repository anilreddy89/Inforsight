CREATE TABLE policy_snapshot (
    snapshot_id VARCHAR(128) PRIMARY KEY,
    policy_id VARCHAR(128) NOT NULL,
    as_of_utc TIMESTAMPTZ NOT NULL,
    evidence_digest CHAR(64) NOT NULL,
    payload_json JSONB NOT NULL,
    created_at_utc TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (policy_id, as_of_utc, evidence_digest)
);

CREATE TABLE control_case (
    case_id VARCHAR(128) PRIMARY KEY,
    policy_id VARCHAR(128) NOT NULL,
    snapshot_id VARCHAR(128) REFERENCES policy_snapshot(snapshot_id),
    state VARCHAR(48) NOT NULL,
    case_version BIGINT NOT NULL CHECK (case_version >= 0),
    recommendation_json JSONB NOT NULL,
    created_at_utc TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at_utc TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE triage_queue (
    queue_entry_id BIGSERIAL PRIMARY KEY,
    case_id VARCHAR(128) NOT NULL REFERENCES control_case(case_id),
    queue_state VARCHAR(48) NOT NULL,
    priority_rank BIGINT NOT NULL,
    allocated_at_utc TIMESTAMPTZ NOT NULL,
    UNIQUE (case_id)
);

CREATE TABLE decision_idempotency (
    case_id VARCHAR(128) NOT NULL REFERENCES control_case(case_id),
    idempotency_key VARCHAR(256) NOT NULL,
    request_digest CHAR(64) NOT NULL,
    response_json JSONB NOT NULL,
    committed_case_version BIGINT NOT NULL,
    created_at_utc TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (case_id, idempotency_key)
);

CREATE TABLE audit_ledger (
    ledger_sequence BIGSERIAL PRIMARY KEY,
    event_id UUID NOT NULL UNIQUE,
    case_id VARCHAR(128) NOT NULL,
    case_version BIGINT NOT NULL CHECK (case_version >= 0),
    event_type VARCHAR(96) NOT NULL,
    actor_id VARCHAR(256) NOT NULL,
    occurred_at_utc TIMESTAMPTZ NOT NULL,
    hash_algorithm VARCHAR(32) NOT NULL,
    canonical_payload TEXT NOT NULL,
    parent_hash CHAR(64) NOT NULL,
    current_hash CHAR(64) NOT NULL UNIQUE,
    created_at_utc TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (case_id, case_version, event_type)
);

CREATE INDEX audit_ledger_case_sequence_idx ON audit_ledger (case_id, ledger_sequence);

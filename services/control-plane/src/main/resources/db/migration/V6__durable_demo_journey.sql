-- Isolated fictional portfolio demo. No customer-action tables or connectors.
CREATE TABLE demo_run (
    correlation_id text PRIMARY KEY,
    event_id text NOT NULL UNIQUE,
    idempotency_key text NOT NULL UNIQUE,
    request_digest text NOT NULL,
    status text NOT NULL,
    document jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE demo_outbox (
    event_id text PRIMARY KEY REFERENCES demo_run(event_id),
    correlation_id text NOT NULL REFERENCES demo_run(correlation_id),
    envelope jsonb NOT NULL,
    published_at timestamptz,
    attempts integer NOT NULL DEFAULT 0,
    last_error text
);
CREATE TABLE demo_inbox (
    event_id text PRIMARY KEY REFERENCES demo_run(event_id),
    correlation_id text NOT NULL REFERENCES demo_run(correlation_id),
    topic text NOT NULL,
    partition_id integer NOT NULL,
    record_offset bigint NOT NULL,
    received_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE demo_case (
    case_id text PRIMARY KEY,
    correlation_id text NOT NULL UNIQUE REFERENCES demo_run(correlation_id),
    version bigint NOT NULL DEFAULT 0,
    state text NOT NULL,
    evidence jsonb NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE demo_decision (
    correlation_id text NOT NULL REFERENCES demo_run(correlation_id),
    idempotency_key text NOT NULL,
    request_digest text NOT NULL,
    response jsonb NOT NULL,
    PRIMARY KEY(correlation_id, idempotency_key)
);
CREATE TABLE demo_journal (
    correlation_id text NOT NULL REFERENCES demo_run(correlation_id),
    sequence bigint NOT NULL,
    event_id text NOT NULL UNIQUE,
    stage text NOT NULL,
    event_type text NOT NULL,
    occurred_at timestamptz NOT NULL,
    producer text NOT NULL,
    canonical_payload text NOT NULL,
    parent_hash text NOT NULL,
    current_hash text NOT NULL,
    PRIMARY KEY(correlation_id, sequence)
);
CREATE TABLE demo_checkpoint (
    correlation_id text PRIMARY KEY REFERENCES demo_run(correlation_id),
    sequence bigint NOT NULL,
    head_hash text NOT NULL
);
CREATE FUNCTION prevent_demo_journal_mutation() RETURNS trigger AS $$
BEGIN RAISE EXCEPTION 'demo journal is append-only'; END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER demo_journal_append_only BEFORE UPDATE OR DELETE ON demo_journal
FOR EACH ROW EXECUTE FUNCTION prevent_demo_journal_mutation();

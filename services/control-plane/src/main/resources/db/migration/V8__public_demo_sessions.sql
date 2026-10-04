-- Public-demo security is separate from the fictional case evidence.
CREATE TABLE demo_session (
    session_id text PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL
);
ALTER TABLE demo_run ADD COLUMN owner_session_id text REFERENCES demo_session(session_id);
ALTER TABLE demo_run ADD COLUMN last_accessed_at timestamptz NOT NULL DEFAULT now();
CREATE INDEX demo_run_owner_status ON demo_run(owner_session_id, status);
CREATE TABLE demo_quota (
    subject text NOT NULL,
    operation text NOT NULL,
    window_start bigint NOT NULL,
    used integer NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY(subject, operation, window_start)
);
CREATE TABLE demo_retention_receipt (
    correlation_id text PRIMARY KEY,
    owner_session_id text NOT NULL REFERENCES demo_session(session_id),
    deleted_at timestamptz NOT NULL DEFAULT now(),
    verified_entries bigint NOT NULL,
    last_verified_head text NOT NULL,
    verification_valid boolean NOT NULL CHECK (verification_valid)
);
-- Regular journal mutation remains forbidden. The only DELETE exception is
-- whole-run retention after verification, in the same transaction as a receipt.
CREATE OR REPLACE FUNCTION prevent_demo_journal_mutation() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'DELETE'
       AND current_setting('inforsight.retention_cleanup', true) = OLD.correlation_id
       AND EXISTS (SELECT 1 FROM demo_retention_receipt t JOIN demo_run r USING(correlation_id)
                   WHERE r.correlation_id = OLD.correlation_id AND r.owner_session_id IS NOT NULL
                     AND r.status IN ('COMPLETED','FAILED','EXPIRED')
                     AND r.updated_at < now() - interval '24 hours'
                     AND t.verification_valid) THEN
        RETURN OLD;
    END IF;
    RAISE EXCEPTION 'demo journal is append-only';
END;
$$ LANGUAGE plpgsql;

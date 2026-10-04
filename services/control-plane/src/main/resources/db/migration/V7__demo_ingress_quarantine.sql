-- Invalid broker records are quarantined before their offset may be committed.
-- Retain only a bounded diagnostic and digest, never an untrusted raw payload.
CREATE TABLE demo_ingress_quarantine (
    topic text NOT NULL,
    partition_id integer NOT NULL,
    record_offset bigint NOT NULL,
    payload_sha256 text NOT NULL,
    error_code text NOT NULL,
    rejected_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY(topic, partition_id, record_offset)
);

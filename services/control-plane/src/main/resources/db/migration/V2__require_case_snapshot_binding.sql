-- A durable case must retain the exact point-in-time snapshot used for its recommendation.
ALTER TABLE control_case
    ALTER COLUMN snapshot_id SET NOT NULL;

CREATE TABLE verification_results_v1 (
    execution_id TEXT PRIMARY KEY
        REFERENCES authorization_snapshots(execution_id),
    execution_epoch INTEGER NOT NULL CHECK(execution_epoch >= 1),
    target_digest TEXT NOT NULL
        CHECK(length(target_digest) = 64 AND target_digest NOT GLOB '*[^0-9a-f]*'),
    runner_observation_digest TEXT NOT NULL
        CHECK(
            length(runner_observation_digest) = 64
            AND runner_observation_digest NOT GLOB '*[^0-9a-f]*'
        ),
    verifier_observation_digest TEXT NOT NULL
        CHECK(
            length(verifier_observation_digest) = 64
            AND verifier_observation_digest NOT GLOB '*[^0-9a-f]*'
        ),
    observed_post_state_digest TEXT NOT NULL
        CHECK(
            length(observed_post_state_digest) = 64
            AND observed_post_state_digest NOT GLOB '*[^0-9a-f]*'
        ),
    verification_boundary_digest TEXT NOT NULL
        CHECK(
            length(verification_boundary_digest) = 64
            AND verification_boundary_digest NOT GLOB '*[^0-9a-f]*'
        ),
    verifier_id TEXT NOT NULL
        CHECK(length(verifier_id) = 64 AND verifier_id NOT GLOB '*[^0-9a-f]*'),
    verifier_identity_digest TEXT NOT NULL
        CHECK(
            length(verifier_identity_digest) = 64
            AND verifier_identity_digest NOT GLOB '*[^0-9a-f]*'
        ),
    verification_strength_digest TEXT NOT NULL
        CHECK(
            length(verification_strength_digest) = 64
            AND verification_strength_digest NOT GLOB '*[^0-9a-f]*'
        ),
    verification_strength_class TEXT NOT NULL
        CHECK(verification_strength_class = 'INDEPENDENT_PROVIDER_READBACK'),
    verdict TEXT NOT NULL CHECK(verdict IN ('VERIFIED', 'NOT_VERIFIED')),
    reason TEXT NOT NULL
        CHECK(reason IN ('OBSERVED_STATE_MATCH', 'OBSERVED_STATE_MISMATCH')),
    checked_at TEXT NOT NULL CHECK(length(checked_at) > 0),
    result_revision TEXT NOT NULL CHECK(length(result_revision) > 0),
    result_digest TEXT NOT NULL UNIQUE
        CHECK(length(result_digest) = 64 AND result_digest NOT GLOB '*[^0-9a-f]*'),
    result_json TEXT NOT NULL CHECK(length(result_json) > 2),
    CHECK(
        (verdict = 'VERIFIED' AND reason = 'OBSERVED_STATE_MATCH')
        OR (verdict = 'NOT_VERIFIED' AND reason = 'OBSERVED_STATE_MISMATCH')
    )
);

CREATE TRIGGER trg_verification_results_v1_binding_insert
BEFORE INSERT ON verification_results_v1
WHEN NOT EXISTS (
    SELECT 1
    FROM dispatch_outbox_v1 AS outbox
    JOIN execution_epoch_state_v1 AS epoch
      ON epoch.execution_id = outbox.execution_id
    WHERE outbox.execution_id = NEW.execution_id
      AND outbox.target_digest = NEW.target_digest
      AND epoch.execution_id = NEW.execution_id
      AND epoch.current_epoch = NEW.execution_epoch
      AND epoch.status = 'COMPLETED'
      AND epoch.completion_digest = NEW.runner_observation_digest
)
BEGIN
    SELECT RAISE(ABORT, 'verification result durable binding is invalid');
END;

CREATE TRIGGER trg_verification_results_v1_immutable_update
BEFORE UPDATE ON verification_results_v1
BEGIN
    SELECT RAISE(ABORT, 'verification result is immutable');
END;

CREATE TRIGGER trg_verification_results_v1_immutable_delete
BEFORE DELETE ON verification_results_v1
BEGIN
    SELECT RAISE(ABORT, 'verification result is immutable');
END;

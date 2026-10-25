-- Migration: MAAI clinician escalations for self-harm / high-risk screenings.

CREATE TABLE IF NOT EXISTS escalations (
    id              TEXT PRIMARY KEY,
    account_id      TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    session_id      TEXT REFERENCES epds_sessions(id) ON DELETE CASCADE,
    mother_id       TEXT,
    reason          TEXT NOT NULL,
    risk_band       TEXT,
    total_score     INT,
    status          TEXT NOT NULL DEFAULT 'open',
    notified        BOOLEAN NOT NULL DEFAULT false,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    acknowledged_at TIMESTAMPTZ,
    resolved_at     TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_escalations_account ON escalations(account_id, created_at DESC);

-- De-duplicate escalations per (session, reason) so re-scoring a call does not
-- raise the same escalation twice.
CREATE UNIQUE INDEX IF NOT EXISTS idx_escalations_session_reason
    ON escalations(session_id, reason) WHERE session_id IS NOT NULL;

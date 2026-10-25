-- Migration: EPDS screening sessions and per-question responses.
-- Scores are computed in application code (see agentline/epds.py), never by
-- the LLM, so results are deterministic and auditable.

CREATE TABLE IF NOT EXISTS epds_sessions (
    id             TEXT PRIMARY KEY,
    account_id     TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    agent_id       TEXT REFERENCES agents(id) ON DELETE SET NULL,
    call_id        TEXT,
    subject_name   TEXT,
    subject_phone  TEXT,
    language       TEXT NOT NULL DEFAULT 'hi',
    status         TEXT NOT NULL DEFAULT 'in_progress',  -- in_progress | completed
    total_score    INT,
    risk_band      TEXT,                                  -- low | medium | high
    self_harm_flag BOOLEAN NOT NULL DEFAULT false,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at   TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_epds_sessions_account
    ON epds_sessions(account_id, created_at DESC);

CREATE TABLE IF NOT EXISTS epds_responses (
    session_id  TEXT NOT NULL REFERENCES epds_sessions(id) ON DELETE CASCADE,
    question_no INT NOT NULL CHECK (question_no BETWEEN 1 AND 10),
    answer      INT NOT NULL CHECK (answer BETWEEN 0 AND 3),  -- chosen option index
    score       INT NOT NULL CHECK (score BETWEEN 0 AND 3),   -- computed EPDS score
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (session_id, question_no)
);

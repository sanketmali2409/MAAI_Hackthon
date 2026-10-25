-- Migration: MAAI mothers registry and consent audit trail.

CREATE TABLE IF NOT EXISTS mothers (
    id            TEXT PRIMARY KEY,
    account_id    TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    name          TEXT,
    phone         TEXT NOT NULL,
    language      TEXT NOT NULL DEFAULT 'hi',
    registered_by TEXT,
    delivery_date DATE,
    call_cadence  TEXT NOT NULL DEFAULT 'weekly',   -- daily | weekly
    next_call_at  TIMESTAMPTZ,
    active        BOOLEAN NOT NULL DEFAULT true,
    notes         TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_mothers_account ON mothers(account_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_mothers_due ON mothers(next_call_at) WHERE active = true;

CREATE TABLE IF NOT EXISTS consent (
    id          TEXT PRIMARY KEY,
    mother_id   TEXT NOT NULL REFERENCES mothers(id) ON DELETE CASCADE,
    account_id  TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    consented   BOOLEAN NOT NULL,
    scope       TEXT,
    method      TEXT,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_consent_mother ON consent(mother_id, recorded_at DESC);

ALTER TABLE epds_sessions
    ADD COLUMN IF NOT EXISTS mother_id TEXT REFERENCES mothers(id) ON DELETE SET NULL;

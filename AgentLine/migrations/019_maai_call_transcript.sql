-- Migration: MAAI store Bolna post-call transcript + execution id on sessions.

ALTER TABLE epds_sessions ADD COLUMN IF NOT EXISTS transcript TEXT;
ALTER TABLE epds_sessions ADD COLUMN IF NOT EXISTS bolna_execution_id TEXT;

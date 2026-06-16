-- UNSEEN PROXY — Phase 4B additive migration.
-- Additive only (ALTER ... ADD COLUMN). No table drops, no column removals, no data rewrites.
-- Backfills are handled by the column DEFAULTs (existing rows inherit them); SQLite ADD COLUMN
-- defaults must be constants (datetime('now') is NOT allowed here), so time columns are NULL
-- and set explicitly by the service code at write time.

-- ---------- idempotency_keys: add lifecycle status + updated_at (§30A.2) ----------
-- Phase 4A had (scope,key,result_ref,created_at). The idempotency contract needs an explicit
-- state machine: 'in_progress' on begin, 'completed' on complete (prior result then replayed).
ALTER TABLE idempotency_keys ADD COLUMN status     TEXT NOT NULL DEFAULT 'in_progress';  -- in_progress|completed
ALTER TABLE idempotency_keys ADD COLUMN updated_at TEXT;                                  -- set by code on completion

-- ---------- outbound_messages: queue payload reference + retry/dead-letter metadata (§30A.3) ----------
-- Phase 4A had (customer_id,channel,purpose,status,attempts,created_at,sent_at).
-- payload_ref points at the message content/template elsewhere — we NEVER store the raw body/secret here.
ALTER TABLE outbound_messages ADD COLUMN payload_ref     TEXT;                  -- reference/handle, NOT the raw body
ALTER TABLE outbound_messages ADD COLUMN last_error      TEXT;                  -- sanitized failure ref, never a secret
ALTER TABLE outbound_messages ADD COLUMN next_attempt_at TEXT;                  -- backoff hint for the (future) sender
ALTER TABLE outbound_messages ADD COLUMN max_attempts    INTEGER NOT NULL DEFAULT 5;  -- dead-letter after this many

CREATE INDEX IF NOT EXISTS idx_outbound_status ON outbound_messages(status);
CREATE INDEX IF NOT EXISTS idx_idempotency_scope_status ON idempotency_keys(scope, status);

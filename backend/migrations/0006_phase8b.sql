-- UNSEEN PROXY — Phase 8B additive migration (portal auth/session foundation).
-- Stores only token/session hashes. Raw portal tokens and raw session ids are never persisted.

CREATE TABLE IF NOT EXISTS portal_access_tokens (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  customer_id        INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  subscription_id    INTEGER REFERENCES subscriptions(id) ON DELETE CASCADE,
  access_profile_id  INTEGER REFERENCES access_profiles(id) ON DELETE SET NULL,
  token_hash         TEXT NOT NULL UNIQUE,
  purpose            TEXT NOT NULL DEFAULT 'branded_subscription',
  status             TEXT NOT NULL DEFAULT 'active',
  created_at         TEXT NOT NULL DEFAULT (datetime('now')),
  expires_at         TEXT NOT NULL,
  revoked_at         TEXT,
  last_verified_at   TEXT
);

CREATE TABLE IF NOT EXISTS portal_sessions (
  id                     INTEGER PRIMARY KEY AUTOINCREMENT,
  customer_id             INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  source_access_token_id  INTEGER REFERENCES portal_access_tokens(id) ON DELETE SET NULL,
  session_hash            TEXT NOT NULL UNIQUE,
  status                  TEXT NOT NULL DEFAULT 'active',
  created_at              TEXT NOT NULL DEFAULT (datetime('now')),
  expires_at              TEXT NOT NULL,
  revoked_at              TEXT,
  last_verified_at        TEXT
);

CREATE INDEX IF NOT EXISTS idx_portal_access_tokens_customer ON portal_access_tokens(customer_id);
CREATE INDEX IF NOT EXISTS idx_portal_access_tokens_sub ON portal_access_tokens(subscription_id);
CREATE INDEX IF NOT EXISTS idx_portal_access_tokens_status_expiry ON portal_access_tokens(status, expires_at);
CREATE INDEX IF NOT EXISTS idx_portal_sessions_customer ON portal_sessions(customer_id);
CREATE INDEX IF NOT EXISTS idx_portal_sessions_status_expiry ON portal_sessions(status, expires_at);


-- UNSEEN PROXY — Phase 4C additive migration (dry-run provisioning orchestration).
-- Additive only (ALTER ADD COLUMN + new FK-enforced table). No drops/renames/rewrites.
-- ADD COLUMN defaults are constants (SQLite forbids datetime('now') there); time columns set by code.

-- ---------- subscriptions: provisioning status axis (separate from lifecycle `status`) ----------
-- `status` stays the lifecycle (pending|active|expired|suspended). `provision_status` tracks the
-- orchestration outcome so a dry-run plan never looks like a live, active subscription.
ALTER TABLE subscriptions ADD COLUMN provision_status TEXT NOT NULL DEFAULT 'unprovisioned';
  -- unprovisioned | dry_run_planned | provision_failed | provisioned

-- ---------- payment_orders: approval timestamp ----------
ALTER TABLE payment_orders ADD COLUMN approved_at TEXT;   -- set by the (dry-run) approval boundary

-- ---------- provisioning_attempts: one row per provisioning attempt (audit/compensation) ----------
CREATE TABLE IF NOT EXISTS provisioning_attempts (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  subscription_id INTEGER NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
  node_code       TEXT REFERENCES proxy_nodes(node_code) ON DELETE SET NULL,
  mode            TEXT NOT NULL DEFAULT 'dry_run',   -- dry_run | live
  outcome         TEXT NOT NULL,                     -- dry_run_planned | live_refused | failed
  reason          TEXT,                              -- sanitized; never secrets/links/UUIDs
  created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_provisioning_attempts_sub ON provisioning_attempts(subscription_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_provision_status ON subscriptions(provision_status);

-- UNSEEN PROXY — Phase 7 additive migration (entitlement + node-resilience foundation).
-- Additive only, FK-enforced. No drops/renames/rewrites.

-- ---------- node-specific protocol availability ----------
-- Protocol availability is naturally per-node (a node may not have a given inbound up). ABSENCE of
-- a row means "available by default" (back-compat: existing flows are unaffected). A row with
-- is_available=0 marks that protocol DOWN on that node, so we can say "protocol unavailable for
-- this region" honestly without silently downgrading.
CREATE TABLE IF NOT EXISTS proxy_node_protocols (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  node_code     TEXT NOT NULL REFERENCES proxy_nodes(node_code) ON DELETE CASCADE,
  profile_code  TEXT NOT NULL REFERENCES protocol_profiles(profile_code) ON DELETE CASCADE,
  is_available  INTEGER NOT NULL DEFAULT 1,
  updated_at    TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE (node_code, profile_code)
);

-- ---------- data-driven per-node live blockers ----------
-- Replaces hardcoding "de1 has leaked keys" in code: the blocker is a DB row (admin-editable).
-- Clearing the blocker = deleting the row (e.g. after the de1 rebuild). Reasons use the Phase 7
-- readiness vocabulary (e.g. leaked_key_rebuild_pending).
CREATE TABLE IF NOT EXISTS node_live_blockers (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  node_code   TEXT NOT NULL REFERENCES proxy_nodes(node_code) ON DELETE CASCADE,
  reason      TEXT NOT NULL,                 -- sanitized reason code; never a secret
  detail      TEXT,                          -- sanitized note; no secrets/links/UUIDs
  created_at  TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE (node_code, reason)
);

CREATE INDEX IF NOT EXISTS idx_proxy_node_protocols_node ON proxy_node_protocols(node_code);
CREATE INDEX IF NOT EXISTS idx_node_live_blockers_node ON node_live_blockers(node_code);

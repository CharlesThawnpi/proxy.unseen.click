-- UNSEEN PROXY — initial schema (Phase 4A foundation).
-- Additive, FK-enforced. No business values here (seeded separately, admin-editable).
-- Money is MMK-only (integer minor units not needed; MMK has no subunit in practice → store whole MMK).

-- ---------- settings (generic DB-driven config) ----------
CREATE TABLE IF NOT EXISTS settings (
  key          TEXT PRIMARY KEY,
  value        TEXT,
  description  TEXT,
  updated_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ---------- identity ----------
CREATE TABLE IF NOT EXISTS customers (
  id                    INTEGER PRIMARY KEY AUTOINCREMENT,
  public_customer_code  TEXT UNIQUE,                       -- e.g. UP0001 (gap-safe: max-id+1)
  preferred_language    TEXT NOT NULL DEFAULT 'my',         -- Burmese-primary
  referral_code         TEXT UNIQUE,
  referred_by_code      TEXT,
  merged_into_customer_id INTEGER REFERENCES customers(id) ON DELETE SET NULL,
  created_at            TEXT NOT NULL DEFAULT (datetime('now')),
  is_deleted            INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS platform_accounts (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  platform_name    TEXT NOT NULL,                           -- telegram|messenger|viber|whatsapp|web
  platform_user_id TEXT NOT NULL,
  customer_id      INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  is_active        INTEGER NOT NULL DEFAULT 1,
  created_at       TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE (platform_name, platform_user_id)
);

CREATE TABLE IF NOT EXISTS account_link_tokens (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  customer_id   INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  code_hash     TEXT NOT NULL UNIQUE,                       -- hashed short code; raw never stored
  created_at    TEXT NOT NULL DEFAULT (datetime('now')),
  expires_at    TEXT NOT NULL,
  consumed_at   TEXT
);

CREATE TABLE IF NOT EXISTS customer_merges (
  id                 INTEGER PRIMARY KEY AUTOINCREMENT,
  source_customer_id INTEGER NOT NULL,
  target_customer_id INTEGER NOT NULL,
  performed_at       TEXT NOT NULL DEFAULT (datetime('now')),
  detail             TEXT
);

-- ---------- catalogue: plans / regions / protocols ----------
CREATE TABLE IF NOT EXISTS plans (
  id                       INTEGER PRIMARY KEY AUTOINCREMENT,
  plan_code                TEXT NOT NULL UNIQUE,            -- TRIAL, BASIC_1M, ...
  display_name_en          TEXT NOT NULL,
  display_name_my          TEXT,
  data_limit_gib           INTEGER NOT NULL,               -- UNSEEN stores GiB; convert to GB for Hiddify
  duration_days            INTEGER NOT NULL,
  price_mmk                INTEGER NOT NULL,
  recommended_device_count INTEGER,
  is_trial                 INTEGER NOT NULL DEFAULT 0,
  is_public                INTEGER NOT NULL DEFAULT 1,
  is_enabled               INTEGER NOT NULL DEFAULT 1,
  sort_order               INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS proxy_regions (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  region_code  TEXT NOT NULL UNIQUE,                        -- de, us, sg
  display_name TEXT NOT NULL,
  status       TEXT NOT NULL DEFAULT 'planned',            -- planned|test|standby|live
  is_default   INTEGER NOT NULL DEFAULT 0,                  -- DE = default/entry
  is_premium_only INTEGER NOT NULL DEFAULT 0,               -- SG = premium-only
  sort_order   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS protocol_profiles (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  profile_code  TEXT NOT NULL UNIQUE,                       -- FAST1, FAST2, SECURE
  display_base  TEXT NOT NULL,                              -- "Fast" / "Secure" (display rule in code)
  engine_protocol TEXT NOT NULL,                            -- hysteria2 | shadowsocks | vless-reality
  is_fast_tier  INTEGER NOT NULL DEFAULT 0,                 -- FAST1/FAST2 = 1; SECURE = 0
  sort_order    INTEGER NOT NULL DEFAULT 0
);

-- ---------- nodes (data, not code) with provenance split (ADR-002) ----------
CREATE TABLE IF NOT EXISTS proxy_nodes (
  id                 INTEGER PRIMARY KEY AUTOINCREMENT,
  node_code          TEXT NOT NULL UNIQUE,                  -- de1, sg1, ...
  region_code        TEXT NOT NULL REFERENCES proxy_regions(region_code) ON DELETE RESTRICT,
  public_hostname    TEXT,                                  -- node-de.unseen.click
  public_ip          TEXT,                                  -- inventory IP (not a secret)
  status             TEXT NOT NULL DEFAULT 'planned',       -- planned|test|standby|live
  is_master_colocated INTEGER NOT NULL DEFAULT 0,           -- co-location RETIRED → 0
  -- secret API key + admin proxy path live in .env, referenced by handle only:
  api_secret_handle  TEXT,                                  -- e.g. NODE_DE1_API_KEY (env var name)
  -- provider/purchase ESTIMATE values:
  est_vcpu           INTEGER, est_ram_mb INTEGER, est_disk_gb INTEGER, est_bandwidth_gb INTEGER,
  -- node-DETECTED values (authoritative once measured):
  det_os             TEXT, det_vcpu INTEGER, det_ram_mb INTEGER, det_disk_gb INTEGER,
  -- provider-CONFIRMED (e.g. bandwidth via provider API):
  conf_bandwidth_gb  INTEGER,
  verification_status TEXT NOT NULL DEFAULT 'unknown',      -- unknown|estimate|detected|provider-confirmed
  notes              TEXT,
  created_at         TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS plan_region_entitlements (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  plan_code   TEXT NOT NULL REFERENCES plans(plan_code) ON DELETE CASCADE,
  region_code TEXT NOT NULL REFERENCES proxy_regions(region_code) ON DELETE CASCADE,
  UNIQUE (plan_code, region_code)
);

CREATE TABLE IF NOT EXISTS plan_protocol_entitlements (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  plan_code    TEXT NOT NULL REFERENCES plans(plan_code) ON DELETE CASCADE,
  profile_code TEXT NOT NULL REFERENCES protocol_profiles(profile_code) ON DELETE CASCADE,
  UNIQUE (plan_code, profile_code)
);

-- ---------- subscriptions / access ----------
CREATE TABLE IF NOT EXISTS subscriptions (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  customer_id     INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  plan_code       TEXT NOT NULL REFERENCES plans(plan_code) ON DELETE RESTRICT,
  -- order-time SNAPSHOTS so later plan edits never invalidate old orders:
  snap_data_limit_gib INTEGER NOT NULL,
  snap_duration_days  INTEGER NOT NULL,
  snap_price_mmk      INTEGER NOT NULL,
  status          TEXT NOT NULL DEFAULT 'pending',          -- pending|active|expired|suspended
  start_date      TEXT,
  expiry_date     TEXT,
  created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- per-customer opaque subscription token (hash only; raw never stored; encrypted-at-rest elsewhere)
CREATE TABLE IF NOT EXISTS access_profiles (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  customer_id      INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  token_sha256     TEXT NOT NULL UNIQUE,
  token_storage_version INTEGER NOT NULL DEFAULT 1,         -- for secret rotation
  hiddify_uuid     TEXT,                                    -- per-customer Hiddify user UUID (treated as secret)
  created_at       TEXT NOT NULL DEFAULT (datetime('now')),
  revoked_at       TEXT
);

-- ---------- payments ----------
CREATE TABLE IF NOT EXISTS payment_methods (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  method_code TEXT NOT NULL UNIQUE,                          -- kpay, wave, manual
  display_name TEXT NOT NULL,
  is_enabled  INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS payment_orders (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  customer_id     INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  plan_code       TEXT NOT NULL REFERENCES plans(plan_code) ON DELETE RESTRICT,
  method_code     TEXT REFERENCES payment_methods(method_code) ON DELETE SET NULL,
  amount_mmk      INTEGER NOT NULL,
  status          TEXT NOT NULL DEFAULT 'pending',           -- pending|review|approved|rejected
  idempotency_key TEXT,
  created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS invoices (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id      INTEGER NOT NULL REFERENCES payment_orders(id) ON DELETE CASCADE,
  doc_type      TEXT NOT NULL,                               -- invoice|receipt (English docs)
  is_prelive    INTEGER NOT NULL DEFAULT 1,                  -- pre-live watermark until launch
  created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ---------- resilience / ops primitives ----------
CREATE TABLE IF NOT EXISTS idempotency_keys (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  scope       TEXT NOT NULL,                                 -- payment_approval | provision | referral_grant
  key         TEXT NOT NULL,
  result_ref  TEXT,
  created_at  TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE (scope, key)
);

CREATE TABLE IF NOT EXISTS outbound_messages (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  customer_id  INTEGER REFERENCES customers(id) ON DELETE CASCADE,
  channel      TEXT NOT NULL,                                -- telegram|messenger|viber|whatsapp
  purpose      TEXT NOT NULL,                                -- transactional|reminder|promo
  status       TEXT NOT NULL DEFAULT 'queued',               -- queued|sent|suppressed|dead
  attempts     INTEGER NOT NULL DEFAULT 0,
  created_at   TEXT NOT NULL DEFAULT (datetime('now')),
  sent_at      TEXT
);

CREATE TABLE IF NOT EXISTS referral_credits (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  customer_id   INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  bonus_days    INTEGER NOT NULL,
  reason        TEXT,
  created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS node_metrics (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  node_code   TEXT NOT NULL REFERENCES proxy_nodes(node_code) ON DELETE CASCADE,
  ts          TEXT NOT NULL DEFAULT (datetime('now')),
  cpu_pct     REAL, ram_pct REAL, disk_pct REAL, bandwidth_gb REAL, users_count INTEGER
);

CREATE TABLE IF NOT EXISTS node_alerts (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  node_code   TEXT NOT NULL REFERENCES proxy_nodes(node_code) ON DELETE CASCADE,
  level       TEXT NOT NULL,                                 -- WARN|CRITICAL|DOWN
  metric      TEXT, value REAL, raised_at TEXT NOT NULL DEFAULT (datetime('now')),
  cleared_at  TEXT
);

CREATE TABLE IF NOT EXISTS audit_logs (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  actor       TEXT,                                          -- admin id / system (sanitized)
  action      TEXT NOT NULL,
  target      TEXT,
  detail      TEXT,                                          -- sanitized; no secrets/PII
  created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_customer ON subscriptions(customer_id);
CREATE INDEX IF NOT EXISTS idx_platform_accounts_customer ON platform_accounts(customer_id);
CREATE INDEX IF NOT EXISTS idx_node_metrics_node_ts ON node_metrics(node_code, ts);

-- UNSEEN PROXY — Phase 6 additive migration (subscription delivery foundation, dry-run).
-- Additive only. The delivery record stores ONLY safe references/metadata — there is
-- DELIBERATELY no column for a raw subscription/proxy link, deep-link payload, or QR payload.
-- The branded opaque token is stored as a HASH/handle only; its raw value never lands in the DB.

CREATE TABLE IF NOT EXISTS subscription_deliveries (
  id                   INTEGER PRIMARY KEY AUTOINCREMENT,
  customer_id          INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  subscription_id      INTEGER REFERENCES subscriptions(id) ON DELETE CASCADE,
  access_profile_id    INTEGER REFERENCES access_profiles(id) ON DELETE SET NULL,
  channel              TEXT NOT NULL,                         -- telegram|messenger|viber|whatsapp
  template_key         TEXT NOT NULL,                         -- payload_ref / template key; never a raw link
  primary_mode         TEXT NOT NULL,                         -- deep_link|copy_link|qr
  deep_link_available  INTEGER NOT NULL DEFAULT 0,
  copy_link_available  INTEGER NOT NULL DEFAULT 0,
  qr_available         INTEGER NOT NULL DEFAULT 0,            -- 0 in Phase 6 (QR planned, not generated)
  branded_token_sha256 TEXT,                                  -- HASH/handle only; raw opaque token NEVER stored
  status               TEXT NOT NULL DEFAULT 'prepared',      -- prepared|queued|sent (dry-run: prepared/queued)
  created_at           TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_subscription_deliveries_customer ON subscription_deliveries(customer_id);
CREATE INDEX IF NOT EXISTS idx_subscription_deliveries_sub ON subscription_deliveries(subscription_id);

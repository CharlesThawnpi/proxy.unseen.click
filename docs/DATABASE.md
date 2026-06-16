# DATABASE

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §30A.1, §30A.2, Appendix A
> **Status:** **Phase 4A — IMPLEMENTED.** Migration-driven SQLite; foundation built and tested (stdlib only).

The data model for UNSEEN PROXY: a SQLite (WAL) database where **all business values are rows, not constants**, with a documented path to Postgres.

> **Built in Phase 4A** (see [PHASE4A_DB_BACKEND_FOUNDATION.md](PHASE4A_DB_BACKEND_FOUNDATION.md)):
> - Schema: `backend/migrations/0001_initial.sql` (FK-enforced; all required tables incl. the `proxy_nodes`
>   provenance split est_/det_/conf_; order-time snapshots on `subscriptions`; idempotency_keys; outbound_messages).
> - Runner: `backend/migrate.py` (ordered, idempotent, `schema_migrations` registry).
> - **Initialize/update:** `python3 bin/init_db.py --db <path>` (migrate + seed; idempotent).
> - **Connection:** always via `backend.db.connect()` → `PRAGMA foreign_keys=ON`, WAL, busy_timeout.
> - **Tests:** `python3 -m unittest discover -s tests -p 'test_*.py'` (migrations/integrity/FK/seed/code/units/client).
> - **Units:** plans store `data_limit_gib`; convert to Hiddify GB via `backend.units` (Hiddify uses GB).

## Engine & storage

- **SQLite (WAL) now.** The engine layer is generalized to "engine/node" so Hiddify slots in cleanly.
- **Postgres path documented.** Every table is reached through a thin data layer; if concurrency outgrows SQLite, migrate to Postgres by swapping the data layer plus a one-time export/import. The Appendix A schema is Postgres-compatible. The migrations registry (below) makes that path orderly rather than a risky one-off.

## Identity model

- **Canonical customer.** `customers.id` (PK) is the single internal identity. A customer may be reached on multiple platforms but is one record.
- **`public_customer_code`** is a UNIQUE customer-facing code allocated gap-safe (next code derived from the current max id + 1) so codes do not reuse or collide. `referral_code` is derived from `public_customer_code`.
- **Platform mapping.** `platform_accounts` maps each platform identity (telegram / messenger / viber / whatsapp / web) to one canonical `customer_id`, UNIQUE on `(platform_name, platform_user_id)`. This is how the same person on different channels resolves to one profile.
- **Cross-platform linking & merge.** `account_link_tokens` issues short, hashed, one-time link codes (24h validity); `customer_merges` records audit/rollback lineage when one profile is absorbed into another, and the absorbed record carries `merged_into_customer_id`.

## Key tables (see Appendix A for full DDL)

The fields below are summarized; **Appendix A of the plan is the authoritative definition.** Do not paste DDL here.

### Identity
- `customers` — canonical customer record (status, language, trial/referral flags, merge lineage).
- `platform_accounts` — per-platform identity mapped to one customer; UNIQUE(platform_name, platform_user_id).
- `account_link_tokens` — hashed one-time codes for cross-platform account linking.
- `customer_merges` — audit/rollback lineage for profile merges.

### Plans & entitlements
- `plans` — plan catalog (code, prices/currency, data limit, duration, device counts, flags).
- `profiles` — protocol-bearing profiles (FAST1 / FAST2 / SECURE ↔ hysteria2 / shadowsocks / vless_reality).
- `proxy_regions` — region inventory and lifecycle status (planned/test/standby/live).
- `proxy_nodes` — per-node inventory, hardware spec, and status; secrets referenced by handle only (live in `.env`). Replacing a node is a row update, never a code change.
- `plan_region_entitlements` — which regions a plan may use (enable/default/label).
- `plan_profile_entitlements` — which profiles a plan may use; PK(plan_code, profile_code).
- `profile_region_availability` / `plan_profile_region_availability` — fine-grained profile/region/node availability and overrides.

### Subscriptions & engine accounts
- `subscriptions` — customer subscription (plan, status, key status, data limit, dates).
- `access_profiles` — one per (customer, region) Hiddify user; holds the stable per-customer engine UUID (`engine_account_ref`) and per-region usage.
- `access_profile_public_tokens` — durable, encrypted per-customer subscription tokens (hash, fingerprint, status, rotation lineage).

### Payments & deliveries
- `payment_methods` — configured payment methods (account details, QR, instructions).
- `payment_orders` — payment lifecycle with price/duration snapshots and verification state.
- `subscription_deliveries` — delivery records (deeplink/copy_link/QR); stores no secret payload.

### Referral
- `referral_credits` — append-only referral ledger; corrections are new rows or status transitions, never in-place mutation.

### Ops
- `settings` — feature flags, bot username, policy markers, and all referral parameters.
- `audit_logs` — sanitized actor/action audit trail.
- `usage_snapshots` — per-subscription/region usage captures.
- `node_metrics` — time-series node telemetry (CPU/RAM/disk/bandwidth/users/reachability) for the dashboard; rolling-window retention.
- `node_alerts` — node alert state with dedup/snooze (warn/critical/down/recovery).

### Integrity & resilience (§30A)
- `schema_migrations` — the migrations logbook: `version` (PK), `name`, `applied_at`, `checksum`. Forward-only, skip-if-applied; guarantees test and live DBs evolve identically (§30A.1).
- `idempotency_keys` — guards payment approval and provisioning against duplicates; `key` (PK), operation, target_ref, status, result_ref (§30A.2).
- `outbound_messages` — retrying notification queue with backoff and dead-letter; stores references, never secrets (§30A.3).
- `connect_samples` — anonymous service telemetry per region/profile; no customer identity, IP, or PII (§30A.4).

## Migrations registry & idempotency (§30A)

- **Migrations logbook (§30A.1).** `schema_migrations` records every ordered structural change. Before applying a migration the runner checks whether the version is recorded and **skips it if so**, so re-running the migration step is safe and never duplicates or errors. Migrations are ordered, forward-only, and reversible-by-design (each ships `up` and, where feasible, `down`); a pre-apply DB backup is taken automatically.
- **Idempotency (§30A.2).** Payment approval and Hiddify provisioning are made idempotent via `idempotency_keys`. Each carries a stable key; if already `completed` the prior result is returned, if `in_progress` the duplicate is refused. This ensures one subscription / one referral reward even on double-taps, webhook re-delivery, or retries.

## Phase 4B additions (IMPLEMENTED — service boundaries + resilience primitives)

> Built in Phase 4B (see [PHASE4B_ACCOUNT_NOTIFICATION_BACKUP.md](PHASE4B_ACCOUNT_NOTIFICATION_BACKUP.md)); **backend-foundation / dry-run only** — no sends, no live mutations.

- **Migration `0002_phase4b.sql` (additive only):**
  - `idempotency_keys` += `status` (`in_progress`→`completed`) + `updated_at` — the §30A.2 state machine.
  - `outbound_messages` += `payload_ref` (reference/handle, **never the raw body**), `last_error` (sanitized ref),
    `next_attempt_at` (backoff hint), `max_attempts` (dead-letter threshold, default 5).
  - Indexes `idx_outbound_status`, `idx_idempotency_scope_status`.
  - `ALTER ADD COLUMN` defaults are constants (SQLite forbids `datetime('now')` there); time columns set by code.
- **Service modules over this schema** (stdlib): `backend/account_service.py` (`platform_accounts`→`customers`,
  gap-safe `public_customer_code`, idempotent), `backend/account_linking.py` (`account_link_tokens`: hash-only,
  one-time, 24h, reason-opaque; merge is dry-run/no-mutation this slice), `backend/notification_service.py`
  (`outbound_messages` queue-first + retry/dead-letter, no sender), `backend/idempotency.py` + `backend/payment_flow.py`
  (`idempotency_keys` begin/complete; dry-run payment/provision boundary).
- **WAL-safe online backup:** `backend/backup.py` + `bin/backup_db.py` use `sqlite3.Connection.backup()` (never a raw
  WAL copy), verify `integrity_check` + `foreign_key_check`, and write a sanitized manifest. See [BACKUPS.md](BACKUPS.md).

## Phase 4C additions (IMPLEMENTED — dry-run provisioning orchestration)

> Built in Phase 4C (see [PHASE4C_DRY_RUN_PROVISIONING.md](PHASE4C_DRY_RUN_PROVISIONING.md)); **dry-run only** — no live
> Hiddify, no real customers, no sends.

- **Migration `0003_phase4c.sql` (additive only):**
  - `subscriptions` += `provision_status` (`unprovisioned|dry_run_planned|provision_failed|provisioned`) — the
    provisioning axis, kept **separate** from lifecycle `status` so a dry-run plan never looks like a live, active sub.
  - `payment_orders` += `approved_at` (dry-run approval timestamp).
  - new **`provisioning_attempts`** (FK→subscriptions, FK→proxy_nodes): `mode` (dry_run|live), `outcome`
    (dry_run_planned|live_refused|failed), sanitized `reason` — append-only audit/compensation trail.
  - Indexes `idx_provisioning_attempts_sub`, `idx_subscriptions_provision_status`. `ALTER ADD COLUMN` defaults are
    constants (SQLite forbids `datetime('now')` there); time columns set by code. Idempotent re-run verified.
- **Services over this schema** (stdlib): `subscription_service` (order-time snapshots, deterministic dates),
  `access_profile_service` (placeholder token hash only — no raw token/URL/UUID), `payment_approval_service` +
  `provisioning_service` (idempotent `payment_approval`/`provision_subscription` scopes; exactly-once),
  `provisioning_plan` (entitlement resolution + sanitized Hiddify mutation intent + live blockers), `compensation`
  (forward-only, non-destructive), `audit` (sanitized `audit_logs`). Reuses `idempotency_keys` + `outbound_messages`.

## Phase 6 additions (IMPLEMENTED — subscription delivery foundation, dry-run)

> Built in Phase 6 (see [PHASE6_SUBSCRIPTION_DELIVERY_FOUNDATION.md](PHASE6_SUBSCRIPTION_DELIVERY_FOUNDATION.md));
> **dry-run only** — no raw links persisted/logged.

- **Migration `0004_phase6.sql` (additive):** new **`subscription_deliveries`** (FK→customers/subscriptions/
  access_profiles) holding **only safe references/metadata** — `channel`, `template_key` (payload_ref),
  `primary_mode`, `deep_link_available`/`copy_link_available`/`qr_available`, `branded_token_sha256` (**hash/handle
  only**), `status`. There is **deliberately no column** for a raw subscription/proxy link, deep-link payload, or QR
  payload (a test asserts this).
- **Services:** `link_renderer` (branded `https://sub.unseen.click/s/<token>` assembled in memory only; token **hash**
  stored; raw-proxy-link detection + redaction), `hiddify_subscription_output` (normalize **mocked** output →
  sanitized summary, raw discarded), `qr_renderer` (QR **planned**, not generated), `delivery_payloads` +
  `subscription_delivery` (prepare → persist safe refs + audit + enqueue notification, `payload_ref` only). Reuses
  `outbound_messages` + `audit_logs`.

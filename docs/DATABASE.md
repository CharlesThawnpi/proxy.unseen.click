# DATABASE

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §30A.1, §30A.2, Appendix A
> **Status:** Phase 1 skeleton — schema decided in plan; schema + migration runner verified in Phase 4

The data model for UNSEEN PROXY: a SQLite (WAL) database where **all business values are rows, not constants**, with a documented path to Postgres.

> Verified in Phase 4 — the schema and migration runner are built in Phase 4. Do not depend on table shapes until then.

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

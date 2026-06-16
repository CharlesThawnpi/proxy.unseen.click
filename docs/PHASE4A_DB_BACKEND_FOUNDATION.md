# PHASE 4A — DB foundation + Hiddify client/orchestrator skeleton (dry-run)

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) Appendix A, §14, §30A; [DECISIONS.md](DECISIONS.md); [HIDDIFY_API_CONTRACT.md](HIDDIFY_API_CONTRACT.md)
> **Status:** **PASS — dry-run/test-safe only.** No live Hiddify mutations; no real customers; no services started. de1 stays `status=test`.

## Run metadata
- Date/time (UTC): 2026-06-16T03:05Z
- Scope: first backend slice — migration-driven SQLite schema, seed catalogue, `hiddify_client.py`, provisioner CLI (dry-run), and stdlib tests. **Out of scope (not built):** Telegram bot, payments, admin UI, portal, sidecar, live provisioning.
- Stack: **stdlib only** (`sqlite3` / `urllib` / `unittest`) — runs on the control-plane Master with no pip installs.

## Files created
- `backend/__init__.py`, `backend/db.py` (connect: `PRAGMA foreign_keys=ON`, WAL, busy_timeout; integrity/FK helpers).
- `backend/migrate.py` (ordered idempotent runner + `schema_migrations` registry; runnable as module or script).
- `backend/migrations/0001_initial.sql` (full schema — see below).
- `backend/units.py` (GiB↔GB), `backend/customer_code.py` (gap-safe max-id+1), `backend/display.py` (Fast-label rule).
- `backend/config.py` (env-handle secrets, no hardcoded values; `LIVE_ENV_LATCH`).
- `backend/seed.py` (idempotent authoritative catalogue + de1 node).
- `backend/hiddify/__init__.py`, `backend/hiddify/client.py` (API v2 wrapper).
- `bin/init_db.py` (migrate + seed), `bin/hiddify_customer_provisioner.py` (CLI).
- `tests/` (3 modules, 17 tests) + `tests/_helper.py`.

## Schema / migrations added (0001_initial)
Tables (FK-enforced, additive): `schema_migrations`, `settings`, `customers`, `platform_accounts`,
`account_link_tokens` (hashed code), `customer_merges`, `plans`, `proxy_regions`, `protocol_profiles`,
`proxy_nodes` (**provenance split:** `est_*` / `det_*` / `conf_*` + `verification_status`; secret API key by
`api_secret_handle` env name only), `plan_region_entitlements`, `plan_protocol_entitlements`, `subscriptions`
(order-time snapshots), `access_profiles` (token SHA-256 + storage version; Hiddify UUID), `payment_methods`,
`payment_orders` (idempotency_key), `invoices`, `idempotency_keys`, `outbound_messages`, `referral_credits`,
`node_metrics`, `node_alerts`, `audit_logs`.

## Seed data added (authoritative; admin-editable, not code constants)
- Plans (data_limit_gib / days / MMK): TRIAL 10/7/0 · BASIC_1M 50/30/3000 · CORE_1M 100/30/5000 · PLUS_3M 360/90/15000
  · PRO_3M 600/90/20000 · MAX_6M 1500/180/30000.
- Regions: `de` (default, status test), `us` (planned), `sg` (**premium-only**, planned).
- Profiles: FAST1=hysteria2, FAST2=shadowsocks, SECURE=vless-reality.
- Entitlements: SG only on PRO/MAX; one Fast tier on TRIAL/BASIC/CORE → "Fast"; both on PLUS/PRO/MAX → Fast1/Fast2.
- Node `de1` (`5.249.160.59`, `node-de.unseen.click`, **status=test**, not co-located; est vs det specs recorded;
  notes: Hiddify v12.3.3 installed, pre-live key-regen/tuning pending).

## Hiddify client implemented behavior (`backend/hiddify/client.py`)
- Config from `NodeApiConfig` (base host + secret proxy path + API key via **env handles**, never hardcoded).
- **Header auth** `Hiddify-API-Key: <admin-UUID>`. Verified endpoints: `GET|POST /user/`, `GET|PATCH|DELETE
  /user/{uuid}/`, `GET /all-configs/?uuid=`. `disable_user` = PATCH `enable:false` (reversible, preferred over delete).
- **GiB→GB conversion at the boundary** (`create_user`/`patch_user` convert `data_limit_gib`→`usage_limit_GB`).
- Timeouts + bounded retries; **structured `HiddifyResult`**; **never logs** secrets/URLs (proxy path) or raw
  subscription/config payloads. Network opener is injectable → tests mock it (no real calls).

## Provisioner CLI (`bin/hiddify_customer_provisioner.py`)
- Subcommands: `audit`, `status`, `validate-contract`, `provision-one --dry-run`, `suspend-one --dry-run`,
  `reconcile-usage --dry-run`. **Default dry-run; DB-only (no network in this phase).**
- **Live double-gate:** requires `UNSEENPROXY_HIDDIFY_PROVISION_LIVE_ENABLED=1` **AND** `--live --confirm`; even then
  Phase 4A refuses live mutations. Sanitized output only (no API key / proxy path / UUIDs / sub links).

## Dry-run / live-safety rules
- No code path performs a live Hiddify mutation in this phase.
- `config.live_latch_enabled()` is the env half; `--live --confirm` the flag half; both required (tested).

## Test commands and results
```
cd /opt/unseen-proxy && python3 -m unittest discover -s tests -p 'test_*.py'
```
**Result: 17 tests, OK.** Covers: migrations apply clean + idempotent; `integrity_check` ok; `foreign_key_check`
empty; FK enforcement; plan seed values; de1 `status=test`; SG excluded from BASIC/CORE; Fast-label rule; gap-safe
customer code; client path builders + `Hiddify-API-Key` header + GiB→GB in payload; disable=PATCH enable:false;
live latch disabled by default + requires exact value; dry-run provision makes no network call.

## Secret-safety result
No secrets in source (env handles only). No `.env`/DB/log files committed (`.gitignore` covers `*.sqlite3`, `data/`;
test DBs live in `/tmp`). No source filename matches the `*secret*`/`*token*`/`*credential*` globs. Pre-commit scan passes.

## Known limits
- No live provisioning, sidecar, bot, payments, admin/portal (later phases).
- `reconcile-usage` is a stub (sweeper lands later). Schema is a foundation — columns will be extended additively.

## Risks / follow-ups
- de1 pre-live tuning still pending (SS/UDP ports, RAM lock, SSH hardening, **regenerate leaked default-user keys**).
- Brain API: design-only ([BRAIN_API_DESIGN.md](BRAIN_API_DESIGN.md)); build is a separate gated task.

## Exact next recommended task
**Phase 4B** — wire AccountService/NotificationService boundaries + idempotency on the payment-approval/provision
path + the outbound-notification queue (still dry-run for Hiddify), and add a WAL-safe online-backup script. Live
Hiddify provisioning on de1 only after its pre-live tuning is done.

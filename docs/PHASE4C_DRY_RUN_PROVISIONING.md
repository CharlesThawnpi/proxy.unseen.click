# PHASE 4C — dry-run provisioning orchestration

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §6, §8, §14, §30A.2, §30A.3; [DECISIONS.md](DECISIONS.md); [PHASE4A_DB_BACKEND_FOUNDATION.md](PHASE4A_DB_BACKEND_FOUNDATION.md); [PHASE4B_ACCOUNT_NOTIFICATION_BACKUP.md](PHASE4B_ACCOUNT_NOTIFICATION_BACKUP.md); [PHASE4_PRELIVE_DE1_TUNING.md](PHASE4_PRELIVE_DE1_TUNING.md)
> **Status:** **PASS — dry-run orchestration only.** No live Hiddify call, no Hiddify user, no real customer/subscription, no message sent, no service started. de1 stays `status=test`; live provisioning hard-disabled.

## Run metadata
- Date/time (UTC): 2026-06-16T04:05Z
- Scope: wire the dry-run subscription/provisioning path across AccountService → payment-approval boundary →
  idempotency → subscription/access-profile creation → Hiddify provisioning **planning** layer → outbound
  notification queue → compensation/rollback model, proving exactly-once orchestration **without** touching live
  Hiddify and **without** sending messages.
- **Out of scope (NOT built):** live Hiddify mutation, Hiddify users, real customers/payments/subscriptions, bot/admin/
  portal/sidecar/API services, Brain API, public endpoints, nginx/TLS, marking de1 live, SG/US nodes.
- Stack: **stdlib only** (`sqlite3` / `hashlib` / `secrets` / `unittest`).

## Files created
- `backend/audit.py` — sanitized `audit_logs` writer (`audit_row` in-transaction / `write_audit` standalone).
- `backend/provisioning_plan.py` — entitlement resolution + candidate nodes + **live blockers** + sanitized Hiddify
  mutation plan (GiB→GB).
- `backend/subscription_service.py` — create subscription from approved order with order-time snapshots.
- `backend/access_profile_service.py` — placeholder access profile (hash only; no raw token/URL/UUID).
- `backend/payment_approval_service.py` — idempotent dry-run approval boundary.
- `backend/provisioning_service.py` — dry-run provisioning + **live hard-refuse** + end-to-end flow orchestrator.
- `backend/compensation.py` — forward-only, non-destructive compensation model.
- `backend/migrations/0003_phase4c.sql` — additive migration (see below).
- CLIs: `bin/approve_payment_dry_run.py`, `bin/provision_subscription_dry_run.py`, `bin/provisioning_flow_smoke.py`.
- Tests: `tests/test_provisioning_plan.py`, `tests/test_provisioning_flow.py`.

## Files changed
- `backend/__init__.py` (`__all__` += Phase 4C modules), `backend/config.py` (`PHASE4C_LIVE_PROVISION_DISABLED`,
  `LEAKED_KEY_REBUILD_PENDING`).
- Docs (below) + regenerated `SOURCE_OF_TRUTH.md`.

## Schema / migrations added (0003_phase4c — additive only)
- `subscriptions` += `provision_status TEXT NOT NULL DEFAULT 'unprovisioned'` (axis separate from lifecycle `status`):
  `unprovisioned | dry_run_planned | provision_failed | provisioned`.
- `payment_orders` += `approved_at TEXT` (set by the dry-run approval boundary).
- new `provisioning_attempts` (FK→subscriptions, FK→proxy_nodes): `mode` (dry_run|live), `outcome`
  (dry_run_planned|live_refused|failed), sanitized `reason`. Append-only audit/compensation trail.
- Indexes `idx_provisioning_attempts_sub`, `idx_subscriptions_provision_status`. Verified: applies after 0001/0002,
  integrity `ok`, FK empty, **idempotent re-run** (`applied 2nd run: []`).

## SubscriptionService behavior
`create_from_order(order_id, now=None)` requires the order to be `approved`, validates `plan_code`, and copies
**order-time snapshots** (`snap_data_limit_gib`/`snap_duration_days`/`snap_price_mmk`) so later catalogue edits never
alter an existing subscription (tested). Lifecycle `status='pending'`, `provision_status='unprovisioned'`. Dates are
deterministic from `now` (expiry = start + `duration_days`), reproducible in tests.

## AccessProfileService behavior
`create_or_reuse(customer_id)` reuses a non-revoked profile or creates one storing **only a 64-hex placeholder token
hash** (pre-image explicitly `dryrun-placeholder:…`, not stored) — **no raw token, no subscription URL, no Hiddify
UUID** (`hiddify_uuid` NULL in dry-run). One profile per customer (reused on duplicate approval).

## ProvisioningPlan behavior
`build_plan(plan_code, preferred_node)` resolves regions/profiles **from DB entitlement rows** (never hardcoded),
applies the FAST display rule, marks premium-only regions (SG), lists candidate nodes with status, and computes quota
(GiB) + `quota_gb` (Hiddify GB). de1 (`status=test`) is `usable_for_dry_run=True`, `usable_for_live=False`.
`hiddify_mutation_plan()` builds the sanitized intended `POST /user/` call (relative path; `usage_limit_GB` converted;
`package_days`; `enable`) — **no API key / admin path / UUID / sub URL / proxy link / QR**. DE = default/entry; SG =
premium-only PRO/MAX; FAST1=Hysteria2, FAST2=Shadowsocks, Secure=VLESS-Reality (from seed).

## HiddifyProvisioningService dry-run behavior
`plan_and_dry_run_provision(subscription_id, node_code='de1', live, confirm)` builds the plan + mutation intent,
records a `provisioning_attempts` row, sets `provision_status='dry_run_planned'`, enqueues the delivery notification,
and audits — **exactly once** (idempotency scope `provision_subscription`, key `sub:<id>`). **Live is hard-refused in
Phase 4C** regardless of `UNSEENPROXY_HIDDIFY_PROVISION_LIVE_ENABLED=1` + `--live --confirm` + node status — blockers
always include `phase4c_live_disabled`, `leaked_key_rebuild_pending`, and `node_not_live:test`. The future live gate
would additionally require node `status=live` and the leaked-key blocker cleared.

## Payment approval dry-run behavior
`approve_order_dry_run(order_id, now=None)` claims the `payment_approval`/`order:<id>` key, validates the order is
`pending|review`, sets it `approved` + `approved_at`, creates the subscription + access-profile placeholder, audits,
and completes idempotently with `result_ref=sub:<id>`. **No payment gateway/OCR.** Duplicate approval replays the prior
result and creates **no** second subscription (tested).

## Notification queue integration
After the dry-run plan, a delivery notification is enqueued via NotificationService — `channel=telegram`,
`purpose=transactional`, `payload_ref="delivery:sub:<id>"` (a **reference only — no link/body/secret**),
`status=queued`. **No real send.** Enqueued exactly once (guarded by the provision idempotency key) — no duplicate on
replay (tested).

## Idempotency behavior
Two exactly-once scopes drive the flow: `payment_approval` (`order:<id>`) and `provision_subscription` (`sub:<id>`).
Same approval key → same subscription; duplicate flow → no duplicate subscription, attempt, or notification (tested:
1 subscription / 1 notification / 1 attempt after two runs). Both keys reach `completed`.

## Audit behavior
Sanitized `audit_logs` rows for: `payment_approval_dry_run`, `subscription_plan_created`,
`provisioning_dry_run_planned`, `notification_queued` (+ `provisioning_failed` / `delivery_enqueue_failed_retry_flagged`
on the compensation paths). Details carry internal ids/quotas only — **no secrets/links/UUIDs/private customer data**
(tested).

## Tests and results
```
cd /opt/unseen-proxy && python3 -m unittest discover -s tests -p 'test_*.py'
```
**Result: 70 tests, OK** (48 prior + 22 new). New coverage: exactly-one subscription on approval; duplicate approval
replays; snapshots copied + immune to later catalogue change; access-profile stores no raw token/UUID; DE/US/SG
entitlements; SG blocked for BASIC/CORE, allowed for PRO/MAX; FAST label rule; GiB→GB in plan + mutation; de1 `test`
blocks live; leaked-key + phase blockers block live; **live refused even with env+flags**; flow makes **no network
call** (urllib patched to throw); delivery notification enqueued with `payload_ref` only; no duplicate notification on
replay; audit rows sanitized; compensation keeps rows forward-only. All Phase 4A/4B tests still pass.

## Secret-safety result
No secrets in source. Plan summary + Hiddify mutation intent are sanitized (no API key / admin path / UUID / sub URL /
proxy link / QR). Access-profile stores a placeholder hash only; notification stores a `payload_ref` only; audit
details are sanitized. No `.env`, DB runtime files, logs, or backups committed. New source filenames don't match the
`*secret*`/`*token*`/`*credential*` globs. Pre-commit scan passes.

## Known limits
- Dry-run only: no real Hiddify user, no real token/URL/UUID, no real send, no scheduler/worker.
- `provision_status='provisioned'` is reserved for the future live phase; not reachable in 4C.
- Compensation is forward-only marking + audit (no automated retry loop yet).

## Live blockers (all present; live intentionally disabled)
- **de1 `status=test`** → `node_not_live:test`.
- **Leaked-key rebuild required** ([PHASE4_PRELIVE_DE1_TUNING.md](PHASE4_PRELIVE_DE1_TUNING.md)) →
  `leaked_key_rebuild_pending`.
- **No real-device protocol PASS yet** (FAST1/FAST2/Secure) — Charles's device test still pending.
- **Live provisioning intentionally disabled in code** (`config.PHASE4C_LIVE_PROVISION_DISABLED`) →
  `phase4c_live_disabled`; live refuses even with env latch + `--live --confirm`.

## Risks / follow-ups
- When live is unblocked: implement real token/UUID handling (encrypted-at-rest), the actual Hiddify create/patch via
  the client (live path), and wire `account_link_merge`/sender once adapters land.
- Keep `provision_status` and lifecycle `status` distinct as more states appear.

## Exact next recommended task
**Phase 5 (Burmese-primary Telegram bot foundation)** wired to AccountService/SubscriptionService/NotificationService
(still dry-run, no live sends until channel adapters + policy land) — **or**, when Charles authorizes de1 to go live,
the **de1 rebuild** (clears `leaked_key_rebuild_pending`) + real-device protocol test, then a separately-gated task to
enable the live provisioning path.

# PHASE 4B — AccountService / NotificationService boundaries + idempotency + WAL-safe backup

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §9.3, §16, §30.3, §30A.2, §30A.3; [DECISIONS.md](DECISIONS.md); [PHASE4A_DB_BACKEND_FOUNDATION.md](PHASE4A_DB_BACKEND_FOUNDATION.md)
> **Status:** **PASS — backend-foundation / dry-run only.** No platform sends, no real customers, no live Hiddify mutations, no services started. de1 stays `status=test`.

## Run metadata
- Date/time (UTC): 2026-06-16T03:30Z
- Scope: second backend slice — service **boundaries** and resilience primitives on top of the Phase 4A schema:
  AccountService (platform identity → one canonical customer), account-link short codes, NotificationService
  (queue-first, no sender), idempotency helpers, a dry-run payment/provision boundary, and a WAL-safe online backup
  script. **Out of scope (NOT built):** Telegram/Messenger/Viber/WhatsApp bot or UI, real payment processing/OCR,
  admin UI, portal, sidecar, Brain API service, live Hiddify provisioning, public endpoints, nginx/TLS, systemd units.
- Stack: **stdlib only** (`sqlite3` / `hashlib` / `secrets` / `unittest`) — no pip on the control plane.

## Files created
- `backend/migrations/0002_phase4b.sql` — additive migration (see Schema changes).
- `backend/account_service.py` — `resolve_customer` / `find_customer` / `public_code`.
- `backend/account_linking.py` — `issue_link_code` / `validate_link_code` / `consume_link_code` (+ result dataclasses).
- `backend/notification_service.py` — `enqueue_notification`, retry/dead-letter helpers, `classify_policy`, `queue_counts`.
- `backend/idempotency.py` — `begin_idempotent` / `complete_idempotent` / `status_of`.
- `backend/payment_flow.py` — `approve_payment_dry_run` / `provision_subscription_dry_run` (dry-run boundary only).
- `backend/backup.py` — `online_backup` / `verify_backup` (WAL-safe online backup + sanitized manifest).
- `bin/backup_db.py` — backup CLI (`--db --out-dir --dry-run --include-env-path`).
- `bin/queue_notifications.py` — **audit/dry-run only** queue report (no send).
- `bin/account_service_smoke.py` — test-safe smoke over all four boundaries (temp DB, sanitized output).
- `tests/test_account_service.py`, `tests/test_account_linking.py`, `tests/test_notification_service.py`,
  `tests/test_idempotency_and_flow.py`, `tests/test_backup.py`.

## Files changed
- `backend/__init__.py` — `__all__` extended with the Phase 4B modules.
- Docs (see "Docs updated" in CHANGELOG): DATABASE, ACCOUNT_LINKING, BACKUPS, BOT_FLOWS, SECURITY, DEPLOYMENT,
  CURRENT_STATUS, CHANGELOG, BRAIN_API_DESIGN; this file created.

## Schema / migrations added (0002_phase4b — additive only)
- `idempotency_keys` += `status TEXT NOT NULL DEFAULT 'in_progress'` (→ `completed`), `updated_at TEXT`.
- `outbound_messages` += `payload_ref TEXT` (reference/handle, **never the raw body**), `last_error TEXT`
  (sanitized ref), `next_attempt_at TEXT` (backoff hint), `max_attempts INTEGER NOT NULL DEFAULT 5`.
- New indexes: `idx_outbound_status`, `idx_idempotency_scope_status`.
- No drops/renames/rewrites. `ALTER ADD COLUMN` defaults are constants (SQLite forbids `datetime('now')` there);
  time columns are set by code at write time. Migration verified: applies clean after 0001, integrity `ok`, FK empty.

## AccountService behavior (`backend/account_service.py`)
- `resolve_customer(conn, platform_name, platform_user_id, profile=None) -> customer_id`:
  - Validates `platform_name ∈ {telegram, messenger, viber, whatsapp, web}` → `UnknownPlatformError` otherwise.
  - If the `platform_accounts` mapping exists → returns the existing `customer_id`.
  - If missing → in **one transaction**: inserts a `customers` row, assigns the gap-safe `public_customer_code`
    (= the row's own id, e.g. `UP0001`; `referral_code` seeded to the same code), inserts the `platform_accounts`
    mapping, returns the new id.
  - **Idempotent:** re-resolving the same pair returns the same id and creates no duplicate rows.
  - **Raw platform id is never the identity** — it is only a lookup key; identity is the internal `customers.id`.
  - `preferred_language` defaults to `my` (Burmese-primary); only a language hint from `profile` is honored — no
    names/handles/PII are stored.

## Account-link token behavior (`backend/account_linking.py`)
- `issue_link_code(conn, customer_id) -> raw_code`: 8-char code from an unambiguous alphabet (no 0/O/1/I/L),
  one-time, **24h** expiry. Stores **only the SHA-256 hash** in `account_link_tokens.code_hash`; the raw code is
  returned once to the caller and **never stored or logged**.
- `validate_link_code(conn, code) -> LinkValidation(valid, customer_id)`: **reason-opaque** — unknown / expired /
  consumed all yield `valid=False` with no reason field (no information leak).
- `consume_link_code(conn, code, (platform, user_id)) -> LinkConsumeResult(status, customer_id)`:
  - target unknown → `linked` (attach mapping to issuer's customer, mark code consumed);
  - target already maps to issuer → `already_linked` (idempotent no-op, code consumed);
  - target maps to a **different** customer → `merge_required_dry_run`: **mutates nothing** (no re-point, no delete,
    no `merged_into`), and does **not** consume the code. TODO(Phase 5+): the gated/audited/reversible merge.
  - re-validate-inside-transaction prevents a TOCTOU double-consume.

## NotificationService behavior (`backend/notification_service.py`)
- `enqueue_notification(conn, customer_id, channel, purpose, payload_ref) -> message_id`: status defaults `queued`,
  attempts `0`. Channel ∈ {telegram, messenger, viber, whatsapp}; purpose ∈ {transactional, reminder, promo}; invalid
  raises `InvalidChannelError` / `InvalidPurposeError`. Stores `payload_ref` (a handle/template id), **never the body**.
- Retry/dead-letter: `mark_sent`, `mark_suppressed`, `mark_failed_or_retry` (attempts++, dead-letters at
  `max_attempts`, else stays `queued` with a `next_attempt_at` backoff hint), `mark_dead`. `last_error` holds a
  sanitized ref only.
- `classify_policy(channel, purpose, within_session=True)` — **placeholder** policy: Telegram sends all purposes;
  Messenger/WhatsApp out-of-window → transactional sends, reminder `template_required`, promo `suppress`; Viber
  out-of-session non-transactional → `queue`. Not the final compliance logic.
- **No real send; no platform API call.** `queue_counts` returns a sanitized status histogram for the audit CLI.

## Idempotency behavior (`backend/idempotency.py`)
- Scopes: `payment_approval`, `provision_subscription`, `referral_grant`, `account_link_merge` (validated).
- `begin_idempotent(scope, key)` → `started` (first caller, inserts `in_progress`) / `already_completed` (replays the
  prior `result_ref`) / `in_progress` (duplicate refused). UNIQUE(scope, key) is the concurrency guard.
- `complete_idempotent(scope, key, result_ref)` → marks `completed`; if already completed, **keeps and returns the
  prior result_ref** (stable replay). All writes transactional.
- `payment_flow.py` proves the contract end-to-end on a **dry-run** boundary: `approve_payment_dry_run` /
  `provision_subscription_dry_run` are exactly-once (second call → `duplicate=True`, same `result_ref`) and create
  **no** subscription/access rows and **no** Hiddify call.

## Backup script behavior (`backend/backup.py`, `bin/backup_db.py`)
- Uses **`sqlite3.Connection.backup()`** — a consistent point-in-time snapshot across WAL. **Never raw-copies** the
  `.sqlite3`/`-wal`/`-shm` files.
- Verifies every snapshot: `PRAGMA integrity_check` must be `ok` and `PRAGMA foreign_key_check` must be empty.
- `--dry-run` plans target paths and writes nothing. `--include-env-path` records the `.env` **path only** as
  metadata; the module **never reads or prints** env contents (`env_contents_backed_up: false` this slice).
- Writes a sanitized JSON manifest (paths only, never values). Production note: backup dir must be **root-only (700)**;
  in production the `.env` is captured **together** with the DB so encrypted tokens stay decryptable
  ([BACKUPS.md](BACKUPS.md)). **No systemd timer/unit created in this task.**

## Tests and results
```
cd /opt/unseen-proxy && python3 -m unittest discover -s tests -p 'test_*.py'
```
**Result: 48 tests, OK** (17 from Phase 4A + 31 new). New coverage: AccountService create + idempotent resolve +
gap-safe code + invalid-platform reject + all allowed platforms; link code stores hash-not-raw, expires/consumes once,
reason-opaque invalid, already-linked idempotency, **merge path is dry-run with no mutation**; NotificationService
enqueue defaults, invalid channel/purpose, sent/retry/dead-letter transitions, policy placeholder, queue counts;
idempotency begin/complete/duplicate/in-progress/no-overwrite/scope isolation; payment & provision dry-run no-duplicate
+ no subscription/access rows created; backup dry-run writes nothing, online backup uses the SQLite backup API and the
restored snapshot passes integrity + FK, no WAL/SHM copied, manifest has paths-not-secrets. Phase 4A tests still pass.

## Secret-safety result
- No secrets in source (env handles only, per Phase 4A). Raw link codes are **never stored or logged** (SHA-256 hash
  only). Notification `payload_ref`/`last_error` are references, **never raw bodies/secrets**. Backup manifest records
  **paths only**; env contents are never read/printed. No `.env`, DB runtime files, logs, or backups committed
  (`.gitignore` covers `*.sqlite3`, `data/`, `backups/`, `logs/`, `tmp/`). New source filenames do **not** match the
  `*secret*`/`*token*`/`*credential*` globs. Pre-commit secret scan passes.

## Known limits
- Account **merge** is a dry-run placeholder (returns `merge_required_dry_run`, mutates nothing) — the real
  gated/audited/reversible merge lands with the bot (Phase 5+).
- Link-code hashing is plain SHA-256 of the normalized code (codes are short-lived/one-time); an env pepper can be
  added additively later.
- NotificationService has **no sender** — `classify_policy` is a conservative placeholder, not final platform
  compliance logic. There is no scheduler/worker yet.
- Backup script has no retention/rotation and no systemd timer yet (Phase 10 production hardening).

## Risks / follow-ups
- de1 pre-live tuning still pending (SS:8388/UDP ports, RAM lock, SSH hardening, **regenerate leaked default-user
  keys**) before any live provisioning.
- Brain API remains **design-only** ([BRAIN_API_DESIGN.md](BRAIN_API_DESIGN.md)).
- When the sender/merge land, wire `account_link_merge` idempotency around the merge and add per-platform policy.

## Exact next recommended task
**Phase 5 (bot foundation) or Phase 4C (provisioning wiring):** either begin the Burmese-primary Telegram bot wired to
AccountService/NotificationService (still no live sends until adapters + policy land), **or** wire the dry-run
provisioner to the idempotency boundary and add the notification sender skeleton — **after** de1 pre-live tuning, which
must be done before the first live Hiddify provisioning.

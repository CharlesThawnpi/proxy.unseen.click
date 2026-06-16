# PHASE 5 — Telegram bot foundation (Burmese-primary, dry-run)

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §9, §10–§13; [DECISIONS.md](DECISIONS.md); [BOT_FLOWS.md](BOT_FLOWS.md); [PHASE4C_DRY_RUN_PROVISIONING.md](PHASE4C_DRY_RUN_PROVISIONING.md)
> **Status:** **PASS — dry-run only.** No Telegram API call, no message sent, no polling/webhook, no service started, no live provisioning. de1 stays `status=test`.

## Run metadata
- Date/time (UTC): 2026-06-16T04:35Z
- Scope: build the Telegram bot **foundation** around the existing Phase 4 services — adapter boundary, Burmese-primary
  message catalogue, command/router skeleton, AccountService identity integration, dry-run onboarding / plan-browsing /
  status flows, queue-only NotificationService integration, and env-driven admin handling.
- **Out of scope (NOT built):** starting the bot, Telegram API calls, message sends, polling/webhook, systemd unit,
  public webhook endpoint, nginx/TLS, admin UI, portal, Brain API, live Hiddify, real subscriptions/payments.
- Stack: **stdlib only** (`os` / `unittest`); no telegram SDK, no network library used for sending.

## Files created
- `backend/bot_context.py` — env-driven admin ids (`ADMIN_TELEGRAM_IDS`, fallback `TELEGRAM_ADMIN_IDS`), safe parse,
  `is_admin`, sanitized `admin_count`, `token_present` (presence only).
- `backend/telegram_adapter.py` — dry-run boundary; `send_message`/`edit_message`/`answer_callback_query` record intent
  to an outbox; **token redaction**; live sends hard-refused.
- `backend/telegram_messages.py` — Burmese-primary message catalogue (English product terms kept).
- `backend/telegram_commands.py` — command constants + defensive `parse_update` (returns `kind="invalid"` on bad shape).
- `backend/bot_flows.py` — DB-driven content builders (plans view, account status, admin summary).
- `backend/telegram_router.py` — routes updates → handlers; AccountService identity; renders via the dry-run adapter.
- CLIs: `bin/telegram_bot_smoke.py`, `bin/render_telegram_messages.py` (temp DB; no send).
- Tests: `tests/test_telegram_bot.py`.

## Files changed
- `backend/__init__.py` (`__all__` += Phase 5 modules), `backend/config.py` (`PHASE5_LIVE_SEND_DISABLED`, env-name
  constants), `.env.example` (added `ADMIN_TELEGRAM_IDS` placeholder; kept `TELEGRAM_ADMIN_IDS` as a documented alias).
- Docs (below) + regenerated `SOURCE_OF_TRUTH.md`. **No schema change** (no migration).

## Telegram adapter behavior
Pure boundary, **dry-run only**. The token is accepted but stored privately (name-mangled), never in a public field,
never logged; `repr()` and `token_fingerprint` show `tg:<botid>:<redacted>` / `tg:<absent>`. `send_message` /
`edit_message` / `answer_callback_query` append a sanitized `OutboxEntry` and return `{"dry_run": true}` — **no network**.
Live sends raise `LiveSendDisabledError` (Phase 5 hard-disables them via `config.PHASE5_LIVE_SEND_DISABLED`).

## Router / command behavior
`parse_update` defensively extracts `from.id` / `chat.id` / text|callback-data, normalizes a leading command (strips
`@botname`), and returns `kind="invalid"` for any malformed update (no crash, no stack trace). `TelegramRouter`
handles `/start`, `/help`, `/plans`, `/account`|`/status`, `/link` (code-entry stub), `/admin` (env-gated), and an
unknown-command fallback — rendering each reply through the dry-run adapter. Invalid updates get a safe Burmese no-op.

## Burmese-primary message catalogue
All user copy lives in `telegram_messages.py` (~90% Burmese / Myanmar script), with English product terms kept verbatim
(Plan, Trial, Basic, Core, Plus, Pro, Max, Fast, Fast1, Fast2, Secure, UNSEEN PROXY). Welcome, main menu, help, plans
header, account status, link prompt, coming-soon, unknown, invalid, admin denial/summary are all keyed for tests.
**Invoices stay English; none are generated here.** No secrets/links/QR in any string.

## AccountService integration
Every real interaction calls `account_service.resolve_customer(conn, "telegram", str(user_id))`. The Telegram user id
is stored as a `platform_accounts` (telegram, <id>) row — it is **never** the customer identity (that's the internal
`customers.id` surfaced as `public_customer_code`). `/start` is idempotent (repeat → same customer, no duplicate).

## Plan rendering behavior
`bot_flows.build_plans_view` reads **public plan rows from the DB** (`is_public=1 AND is_enabled=1`, ordered by
`sort_order`) — values are never hardcoded in the bot. Per plan it resolves regions/profiles from DB entitlements and
applies the FAST display rule: **DE = default/entry**, **SG = premium-only** (annotated, present only for PRO/MAX),
one fast tier → "Fast", both → "Fast1"/"Fast2", Secure always "Secure". Removing a plan row removes it from the view
(tested — proves DB-driven).

## Notification queue integration
The bot integrates with NotificationService **queue-only**: it can enqueue an internal `outbound_messages` row with a
`payload_ref` (e.g. `bot:welcome:<id>`) — a **reference only, never a raw body/link/secret** — `status=queued`. **No
real send** (the sender lands with channel adapters in a later phase).

## Admin env handling
Admin ids come from `ADMIN_TELEGRAM_IDS` (comma-separated ints; fallback `TELEGRAM_ADMIN_IDS`), parsed defensively
(blanks/non-ints ignored; `__PLACEHOLDER__`/`replace_me` treated as none). **No hardcoded admin id.** The full list is
never logged/rendered — only `admin_count`. `/admin` returns a DB-only sanitized summary (counts) for admins; everyone
else gets a Burmese denial.

## Dry-run / no-send guarantees
- `config.PHASE5_LIVE_SEND_DISABLED = True`; the adapter refuses live sends.
- No polling, no webhook, no Telegram API call, no systemd unit, no public endpoint.
- A test patches `urllib.request.urlopen` to throw and runs the full router flow → proves **no network call**.

## Tests and results
```
cd /opt/unseen-proxy && python3 -m unittest discover -s tests -p 'test_*.py'
```
**Result: 89 tests, OK** (70 prior + 19 new). New coverage: adapter dry-run records no network; live send refused;
token redaction (synthetic token never appears); admin ids parsed from env (+ fallback, + placeholder→none, + empty);
`/start` creates customer + telegram platform account and is idempotent; telegram id ≠ customer identity; invalid/
malformed updates don't crash; unknown-command fallback; plans render from DB (removing a row removes it); SG only for
PRO/MAX; FAST label rule (Fast vs Fast1/Fast2); Burmese present in welcome/menu/help; notification enqueue stores
payload_ref only; no secrets in rendered text; full flow makes no network call. All Phase 4A/4B/4C tests still pass.

## Secret-safety result
No secrets in source/docs/tests. Bot token read by **env name only**, never stored publicly, never logged, redacted in
`repr`. Admin ids env-driven; full list never rendered. `.env.example` carries placeholders only. Notification stores a
`payload_ref` only. Messages/flows carry no token/UUID/link/QR/admin path/payment ref. New source filenames don't match
the `*secret*`/`*token*`/`*credential*` globs. Pre-commit scan passes.

## Known limits
- No live transport: no polling/webhook, no real send — the router renders into a dry-run outbox.
- `/link` is a prompt stub (consume wiring + merge land later); `/account` shows a placeholder/coming-soon when no
  subscription exists.
- No keyboards/inline-button payloads beyond text (callback parsing is supported but UI markup is later).

## Live blockers (intentional)
- **No polling/webhook yet** — bot is not started.
- **No real Telegram send** — `PHASE5_LIVE_SEND_DISABLED`; adapter refuses live.
- **No live provisioning** — Phase 4C live path stays hard-disabled.
- **de1 rebuild still required** before real Hiddify provisioning (leaked-key blocker, [PHASE4_PRELIVE_DE1_TUNING.md](PHASE4_PRELIVE_DE1_TUNING.md)).

## Risks / follow-ups
- When transport lands: add the real send path behind a double gate (`ALLOW_LIVE_BOT_SENDS` + explicit flags) + the
  NotificationService sender/worker + per-platform policy; wire `/link` consume + merge; add inline keyboards.
- Keep all copy in `telegram_messages.py`; add Messenger/Viber/WhatsApp adapters reusing the router/flows.

## Exact next recommended task
**Phase 5 transport (gated) or Phase 6 (subscription delivery):** add the NotificationService **sender** + a gated bot
runner (long-poll) that consumes `outbound_messages` — still no live customer until de1 is rebuilt and a real-device
FAST1/FAST2/Secure PASS is recorded. Live promotion stays Charles-gated.

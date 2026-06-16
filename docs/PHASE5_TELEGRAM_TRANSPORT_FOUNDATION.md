# PHASE 5 — Telegram transport foundation (gated; dry-run)

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §9–§13, §30A.3, §30.4; [DECISIONS.md](DECISIONS.md); [PHASE5_TELEGRAM_BOT_FOUNDATION.md](PHASE5_TELEGRAM_BOT_FOUNDATION.md); [BOT_FLOWS.md](BOT_FLOWS.md)
> **Status:** **PASS — dry-run only, gated.** No Telegram API call, no message sent, no polling daemon, no webhook, no systemd service. de1 stays `status=test`; live provisioning still blocked.

## Run metadata
- Date/time (UTC): 2026-06-16T05:05Z
- Scope: add the **safe transport layer** around the Phase 5 dry-run bot — a Bot API transport
  boundary (`getUpdates`/`sendMessage`/…), an offset-tracking long-poll **runner skeleton**, a
  NotificationService **sender** that consumes `outbound_messages`, and a centralized **runtime
  double-gate**. Default everywhere is dry-run/no-network; live send/poll are hard-refused unless
  both the env latch AND explicit CLI flags are present.
- **Out of scope (NOT done):** starting polling, any Telegram API call, real sends, webhook,
  systemd unit, public endpoint, nginx/TLS, admin UI, portal, Brain API, live Hiddify, real
  subscriptions/payments.
- Stack: **stdlib only** (`urllib` present but its real path is never exercised; tests inject a mock opener).

## Files created
- `backend/runtime_gates.py` — fail-closed `live_send_gate` / `live_poll_gate` (env `1` + flags).
- `backend/telegram_transport.py` — Bot API boundary; dry-run default; injectable `opener`; token redacted.
- `backend/telegram_polling.py` — `TelegramPollingRunner` (offset-tracked; routes via `TelegramRouter`; live refused).
- `backend/notification_sender.py` — consumes queued telegram `outbound_messages`; status transitions; gated.
- `backend/outbound_worker.py` — thin single-pass orchestrator over the sender.
- CLIs: `bin/telegram_poll_dry_run.py`, `bin/outbound_worker_dry_run.py`, `bin/send_notification_dry_run.py`.
- Tests: `tests/test_telegram_transport.py`.

## Files changed
- `backend/__init__.py` (`__all__` += transport modules), `backend/config.py` (`ALLOW_LIVE_BOT_SENDS_ENV`,
  `ALLOW_LIVE_BOT_POLLING_ENV`), `backend/telegram_messages.py` (`render_payload` template resolver),
  `.env.example` (`ALLOW_LIVE_BOT_SENDS=0`, `ALLOW_LIVE_BOT_POLLING=0`). Docs (below) + regenerated SOT.
- **No schema change** (reuses `outbound_messages`, `platform_accounts`).

## TelegramTransport behavior
Wraps `getUpdates`, `sendMessage`, `editMessageText`, `answerCallbackQuery`. The network call is an
**injectable `opener`** (tests pass a mock; **no real network**). **Dry-run by default** (`live=False`):
each call records a sanitized `TransportRequest` to an in-memory outbox and returns a synthetic
`TransportResult(dry_run=True)`. Live mode needs `live=True` + an opener; the real `urllib` path exists but is
never exercised in this task. **Secret-safety:** the token is name-mangled (never a public field), never logged;
the API URL (`/bot<token>/<method>`) is built only inside `_request` and is **never** logged/returned/raised — errors
carry the **method name only**; `repr`/`token_fingerprint` are redacted. **Timeout/retry:** `timeout` (10s default)
bounds each call; `retries` (2 default) with linear backoff for transient errors; 4xx is not retried.

## Polling runner behavior
`TelegramPollingRunner.poll_batch(updates)` routes a provided (fixture) or transport-fetched batch through the real
`TelegramRouter`, tracking the Telegram **offset** (`update_id + 1`). Malformed updates route to a safe `invalid`
result (no crash). **No persistent daemon** is started. `run_live_once(live_poll, confirm)` enforces the double gate
via `runtime_gates.live_poll_gate` and **raises `LivePollingRefusedError`** unless allowed — and even when allowed it
processes a single batch only (no loop).

## Notification sender / outbound worker behavior
`NotificationSender.process_queued()` selects `channel='telegram' AND status='queued'` rows, resolves the recipient
chat id from `platform_accounts` (numeric telegram id), renders Burmese-primary text from the row's **`payload_ref`**
(template key — never a raw body/secret) via `telegram_messages.render_payload`, and "sends" through the (dry-run)
transport. Status transitions use the existing NotificationService helpers:
- success → `sent`; retryable failure → stays `queued` (attempts+1, `next_attempt_at` backoff); permanent / max
  attempts → `dead`. A `simulate` hook drives outcomes deterministically in tests. **Live send is hard-refused**
  unless `runtime_gates.live_send_gate` passes; even gated, tests inject a mock transport. `outbound_worker.run_once`
  is the single-pass CLI entry (no daemon).

## Runtime gate behavior
Centralized, **fail-closed**:
- live send needs env `ALLOW_LIVE_BOT_SENDS=1` (exact `"1"`) **and** `--live-send --confirm`.
- live poll needs env `ALLOW_LIVE_BOT_POLLING=1` (exact `"1"`) **and** `--live-poll --confirm`.
Any missing/invalid piece → `GateDecision(allowed=False, blockers=[...])` with sanitized reasons; never raises on bad
config. Tested: nothing-set, env-missing, flag-missing, and non-`"1"` env values all refuse.

## Dry-run / no-network guarantees
- Default transport mode is dry-run (records intent; returns synthetic result).
- `config.PHASE5_LIVE_SEND_DISABLED` remains for the adapter; transport adds the env+flag double gate.
- A test patches `urllib.request.urlopen` to throw and runs the full poll→route + worker→send path → proves **no
  network call**. CLIs print sanitized counts only and refuse live without the gate.

## Tests and results
```
cd /opt/unseen-proxy && python3 -m unittest discover -s tests -p 'test_*.py'
```
**Result: 107 tests, OK** (89 prior + 18 new). New coverage: transport dry-run records no network; token redacted in
`repr`/fingerprint and the token-URL never exposed; `sendMessage` params carry no token (mock opener); `getUpdates`
offset param; gates fail-closed (send + poll; strict `"1"`); polling routes `/start` and tracks offset; invalid
updates in a batch don't crash; live poll refused without gate; sender marks sent on mock success; retryable failure
keeps queued + attempts++ + `next_attempt_at`; permanent/max-attempts → dead; `payload_ref` only (no raw body); live
send refused without gate; live path uses a **mock** transport even when gated; full dry-run makes no network call. All
Phase 4/5 tests still pass.

## Secret-safety result
No secrets in source/docs/tests. Bot token read by env **name** only, name-mangled, never logged, redacted; the
token-bearing API URL is never logged/returned. Admin ids stay env-driven (never logged). `outbound_messages` stores a
`payload_ref` only — no body/link/token/QR. `.env.example` has gate placeholders (`0`) only. New source filenames
don't match the `*secret*`/`*token*`/`*credential*` globs. Pre-commit scan passes.

## Known limits
- No daemon/loop: `poll_batch` / `run_once` are single-pass. A real long-poll worker + scheduler is a later task.
- Live paths are written but never exercised (no real opener wired); the real `urllib` branch is untested by design.
- `render_payload` covers `bot:welcome*` / `delivery:sub*` / generic; richer templates land with the flows.

## Live blockers (intentional)
- **No systemd service yet** — nothing is installed or started.
- **Live polling not enabled** — refused without `ALLOW_LIVE_BOT_POLLING=1` + `--live-poll --confirm`.
- **Live sends not enabled** — refused without `ALLOW_LIVE_BOT_SENDS=1` + `--live-send --confirm`.
- **No live provisioning** — Phase 4C live path stays hard-disabled.
- **de1 rebuild still required** before real Hiddify provisioning (leaked-key blocker, [PHASE4_PRELIVE_DE1_TUNING.md](PHASE4_PRELIVE_DE1_TUNING.md)).

## Risks / follow-ups
- When going live: wire a real opener + a gated long-poll loop/worker (systemd timer or service), add send
  rate-limiting/backoff tuning, per-platform policy enforcement at send time, and opt-out/block handling.
- Keep the token strictly inside the transport; never let a caller pass the URL around.

## Exact next recommended task
**Phase 6 (subscription delivery) or the gated live bot bring-up:** build the delivery content path (deep-link/QR
generated in memory, never persisted) feeding `payload_ref`s the sender renders — still dry-run until **de1 is rebuilt**
(clears `leaked_key_rebuild_pending`) and a real-device FAST1/FAST2/Secure PASS is recorded. Enabling live polling/sends
is a separate, Charles-gated task that flips the env latches + wires a real opener.

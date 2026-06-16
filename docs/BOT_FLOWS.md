# BOT FLOWS — Multi-platform identity & messaging policy

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §9 (9.1, 9.2), §10–§13
> **Status:** Phase 1 skeleton — decided from plan; per-platform compliance contracts verified at each channel's launch gate

How every front-end platform resolves to one customer, how outbound messages are kept compliant, and the policy contract each platform must satisfy before it goes live.

## Unified identity model

- **Canonical identity:** `customers.id` (`customer_id`) + `public_customer_code` (e.g. `UP0001`, human-readable, given to support — never links accounts by itself).
- **Platform identities:** one `platform_accounts` table maps `(platform_name, platform_user_id) → customer_id` for `telegram`, `messenger`, `viber`, `whatsapp`, `web`.
- A customer can have several platform accounts; all point at one `customer_id` (linking: see [ACCOUNT_LINKING.md](ACCOUNT_LINKING.md)).

## Service boundaries

> **Phase 4B status:** the backend boundaries are **implemented (no bot UI, no sender)** —
> [PHASE4B_ACCOUNT_NOTIFICATION_BACKUP.md](PHASE4B_ACCOUNT_NOTIFICATION_BACKUP.md). AccountService resolves identity;
> NotificationService is **queue-first only** (enqueue + retry/dead-letter + a placeholder policy classifier). No
> message is sent and no platform API is called yet — the channel adapters and final compliance logic land per channel.

- **AccountService** (`backend/account_service.py`) — `resolve_customer(platform_name, platform_user_id, profile=None) → customer_id`. Idempotent; creates the customer on first contact and back-fills the platform mapping. Every handler resolves identity through this, **never** by raw platform id. Cross-platform linking via `backend/account_linking.py` (hash-only one-time 24h codes; merge is dry-run this slice).
- **NotificationService** (`backend/notification_service.py`) — the **single enforcement point** for messaging policy: it classifies each outbound message by purpose (transactional reply / proactive reminder / promotional) and, per the destination channel's policy, **sends now**, **holds in the `outbound_messages` queue** until a valid window opens, **sends via an approved template**, or **suppresses** it if no compliant path exists. Business code never decides this. *Implemented now:* `enqueue_notification` (queue-first, stores a `payload_ref` not the raw body), `mark_sent`/`mark_failed_or_retry`/`mark_dead` (retry → dead-letter at `max_attempts`), and a placeholder `classify_policy(channel, purpose, within_session)`. *Not yet:* the actual `notify_customer` sender + per-channel adapters + final compliance contracts.

## Channel adapter pattern

The bot core is platform-agnostic. Each platform has a thin **adapter** that:
1. receives inbound events and normalizes them to a common incoming message/intent shape;
2. renders outbound messages/buttons to that platform's API;
3. **declares its capabilities and policy** (buttons? deep-link buttons? file upload? proactive window?) — this declaration is what NotificationService enforces.

The business flows (register → plan → pay → deliver → support) are written **once** against the common shape.

## Platform messaging-policy matrix

| Capability | Telegram | Messenger | Viber | WhatsApp |
|---|---|---|---|---|
| Proactive (unprompted) messages | Allowed | Restricted to 24h window + approved templates | Restricted (session/templated) | Restricted to approved templates |
| Rich buttons / inline keyboards | Yes | Yes (quick replies/buttons) | Yes (keyboards) | Limited (list/reply buttons) |
| Deep-link button (`hiddify://…`) | Yes (URL button) | Via URL button / fallback link | Via URL | Via link |
| File/image upload from user | Yes | Yes | Yes | Yes |

Implication: expiry/renewal reminders are **push on Telegram** but must be **queued/templated on Messenger/WhatsApp**. NotificationService encapsulates this so business code stays unaware.

## Platform-first compliance principle (§9.1)

For every front-end we plan to that platform's own rules **first**, and build message content/types/timing to comply **before** the channel launches. A channel does not go live until its compliance plan is written and signed off (gate below). This protects the business: a Meta Page ban, a rejected app review, or a flagged WhatsApp number takes a whole channel offline.

## Per-channel launch compliance gate (§9.2)

Before any new channel is enabled, complete and sign off its checklist:

- [ ] Platform account/app created with correct permissions; **app review submitted and approved** where required (Meta).
- [ ] Platform messaging policy documented here (per-platform section) and encoded in the adapter's declared capabilities.
- [ ] All **proactive message types** (expiry reminders, delivery notices, referral grants) mapped to a **compliant delivery path** (in-window free-form vs. approved template), with templates **submitted and approved** ahead of time.
- [ ] Opt-in/opt-out and block/stop handling verified.
- [ ] Test confirming NotificationService correctly **queues/templates/suppresses** out-of-window messages (not just sends them).

Review lead time (especially Meta/BSP template and app approval) is planned **before** the phase starts.

**Build order:** Telegram first (Phase 5); Messenger and Viber (Phase 9); WhatsApp later (Phase 9+ / post-launch).

---

## Telegram (Phase 5 — built first)

- **Policy contract:** Bot API terms; avoid unsolicited bulk messaging; respect user block/stop. Most permissive platform, but not unlimited; the platform-first principle still applies.
- **Transport:** `python-telegram-bot` (async); long-polling for internal beta, optional webhook on `bot.unseen.click` for production.
- **Capabilities:** inline keyboards, URL deep-link buttons (`hiddify://import/…`), file/image upload, proactive push allowed.
- **Flow:** `/start` → resolve/create customer → View Plans → Buy (upgrade vs additional; price/cap/duration snapshot) → Pay (per-order note + screenshot) → Verify (Tesseract OCR auto-approve else admin) → Deliver (deep-link button + copy-link + QR + guide + invoice/receipt PDFs) → My Account → Support. Admin mode gated.
- **Reminders:** sent as push (allowed).

## Messenger (Phase 9)

- **Policy contract:** the **24-hour standard messaging window** — free-form replies only within 24h of the user's last message. Outside it, only an **approved message tag / template** for permitted purposes (e.g. account update) may be sent — **never marketing**. Requires a Facebook Page + App with `pages_messaging` and **Meta app review**; respect promotional-content policy and opt-out.
- **Transport:** Messenger Platform via Graph API; webhook-based on `bot.unseen.click`, verifying `X-Hub-Signature` (app secret) on every inbound.
- **Adapter:** PSID → `customer_id`; renders to quick replies / button templates / generic templates; enforces the 24h window.
- **Delivery:** URL button with `hiddify://import/<sub-link>` + copy link + "Open guide" button; invoice/receipt PDFs as file attachments.
- **Reminders:** queued; sent on next inbound or via an approved template tag.

## Viber (Phase 9)

- **Policy contract:** Public Account / Bot rules — a user must have a **session** or be **subscribed** to receive messages; session/templated limits apply; respect Viber's commercial-message rules.
- **Transport:** Viber Bot REST API; webhook (`set_webhook` to `bot.unseen.click`); requires a Viber Public Account/Bot + auth token.
- **Adapter:** validate `X-Viber-Content-Signature`; Viber user id → `customer_id`; renders to Viber keyboards (rich media carousels for plans, URL buttons for the deep link); handles session/subscription rules.
- **Delivery:** deep-link import works via URL button; screenshots arrive as media messages for OCR.
- **Reminders:** follow Viber's messaging rules via NotificationService.

## WhatsApp (later — Phase 9+ / post-launch)

- **Policy contract:** the **24-hour customer-service window** for free-form replies; outside it only **pre-approved templates** (utility/authentication/marketing categories) may be sent; **opt-in and opt-out handling is mandatory**; template approval has lead time. Limited interactive messages (list/reply buttons).
- **Transport (future):** WhatsApp Business Platform (Cloud API) via Meta, or a BSP.
- **Adapter:** WhatsApp phone-number id → `customer_id`; all proactive messaging routed through templated sends in NotificationService. No business-logic changes needed (adapter boundary).
- **Reminders:** templated only outside the window.

## Phase 5 — Telegram bot foundation IMPLEMENTED (dry-run, 2026-06-16)

The Burmese-primary Telegram foundation now exists ([PHASE5_TELEGRAM_BOT_FOUNDATION.md](PHASE5_TELEGRAM_BOT_FOUNDATION.md))
— **dry-run only: no polling/webhook, no Telegram API, no send, no service started.**

- **`backend/telegram_adapter.py`** — pure boundary; `send_message`/`edit_message`/`answer_callback_query` record intent
  to an outbox (no network); token is redacted in all output; live sends hard-refused (`config.PHASE5_LIVE_SEND_DISABLED`).
- **`backend/telegram_router.py`** + **`telegram_commands.py`** — defensive `parse_update` (malformed → safe no-op) and
  handlers for `/start`, `/help`, `/plans`, `/account`|`/status`, `/link` (stub), `/admin` (env-gated), unknown fallback.
- **`backend/telegram_messages.py`** — all copy in one place, ~90% Burmese with English product terms kept
  (Plan/Trial/Basic/Core/Plus/Pro/Max/Fast/Fast1/Fast2/Secure). Invoices stay English; none generated here.
- **`backend/bot_flows.py`** — plan list, account status, and admin summary built from **DB rows** (DE default, SG
  premium-only PRO/MAX, FAST display rule) — never hardcoded.
- **Identity:** `/start` → `AccountService.resolve_customer("telegram", <id>)`; the Telegram id is a `platform_accounts`
  key, never the customer identity; idempotent.
- **Admin:** `ADMIN_TELEGRAM_IDS` (fallback `TELEGRAM_ADMIN_IDS`), parsed safely, never logged; `/admin` = DB-only
  sanitized counts. **NotificationService** integration is queue-only (`payload_ref`, no body/secret).

## Phase 5 — gated transport foundation IMPLEMENTED (dry-run, 2026-06-16)

The transport layer now exists ([PHASE5_TELEGRAM_TRANSPORT_FOUNDATION.md](PHASE5_TELEGRAM_TRANSPORT_FOUNDATION.md)) —
**dry-run only, gated: no Telegram API call, no send, no polling daemon, no webhook, no systemd.**

- **`backend/telegram_transport.py`** — Bot API boundary (`getUpdates`/`sendMessage`/`editMessageText`/
  `answerCallbackQuery`); network `opener` is injectable (mock in tests); dry-run records intent (no network); the bot
  token is name-mangled/redacted and the token-bearing API URL is never logged/returned.
- **`backend/telegram_polling.py`** — `TelegramPollingRunner` routes a fetched/fixture batch through `TelegramRouter`,
  tracking the `update_id` offset; **no daemon**; live polling refused without the double gate.
- **`backend/notification_sender.py` + `outbound_worker.py`** — consume queued `outbound_messages` (channel=telegram),
  render Burmese-primary text from the row's `payload_ref` (template key only — no body/link/secret), and transition
  `queued → sent` (success) / `queued` (retryable, attempts++ + backoff) / `dead` (permanent or max attempts). This is
  the concrete NotificationService send path the matrix above anticipated; live send refused without the gate.
- **`backend/runtime_gates.py`** — fail-closed double gate: live send needs `ALLOW_LIVE_BOT_SENDS=1` + `--live-send
  --confirm`; live poll needs `ALLOW_LIVE_BOT_POLLING=1` + `--live-poll --confirm`.

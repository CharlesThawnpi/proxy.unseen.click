# PHASE 6 — subscription delivery foundation (dry-run)

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §16, §30A.3, §31; [DECISIONS.md](DECISIONS.md); [HIDDIFY_API_CONTRACT.md](HIDDIFY_API_CONTRACT.md); [PHASE5_TELEGRAM_TRANSPORT_FOUNDATION.md](PHASE5_TELEGRAM_TRANSPORT_FOUNDATION.md); [SUBSCRIPTION_ACCESS_POLICY.md](SUBSCRIPTION_ACCESS_POLICY.md)
> **Status:** **PASS — dry-run only.** No live Hiddify call, no real subscription fetch from de1, no Telegram send, and **no raw subscription/proxy link or QR payload is ever persisted or logged**. de1 stays `status=test`.

## Run metadata
- Date/time (UTC): 2026-06-16T05:35Z
- Scope: build the subscription **delivery foundation** — a safe delivery payload model, branded
  link / deep-link / copy-link / QR fallback rules, a mocked Hiddify subscription-output
  normalizer, and integration with the NotificationService/Telegram render path. All dry-run.
- **Out of scope (NOT done):** fetching real subscription output from de1, any live Hiddify/Telegram
  call, creating users/customers/subscriptions, sending messages, starting services, QR generation,
  public endpoints, nginx/TLS, Brain API, marking de1 live.
- Stack: **stdlib only** (`hashlib`/`re`/`unittest`); no QR/image dependency added.

## Files created
- `backend/link_renderer.py` — branded link shape + token **handle** (hash), redaction, raw-proxy-link detection.
- `backend/qr_renderer.py` — QR honestly modeled as **planned** (not generated; no risky dep).
- `backend/hiddify_subscription_output.py` — normalize **mocked** output → sanitized summary.
- `backend/delivery_payloads.py` — `DeliveryPayload` (safe refs/flags only; mode priority).
- `backend/subscription_delivery.py` — `prepare_delivery` (persist safe refs + audit + enqueue), `render_preview`.
- `backend/migrations/0004_phase6.sql` — `subscription_deliveries` table (no raw-link/token/QR column).
- CLIs: `bin/subscription_delivery_smoke.py`, `bin/render_delivery_dry_run.py`.
- Tests: `tests/test_subscription_delivery.py`.

## Files changed
- `backend/__init__.py` (`__all__` += Phase 6 modules), `backend/telegram_messages.py` (`delivery_preview`).
- Docs (below) + regenerated SOURCE_OF_TRUTH.md.

## Delivery payload model
`DeliveryPayload` carries **only safe references/metadata**: `customer_id` / `subscription_id` /
`access_profile_id`, `channel`, `template_key` (the `payload_ref`, e.g. `delivery:sub:7`), the mode flags
`deep_link_available` / `copy_link_available` / `qr_available`, the chosen `primary_mode`, and
`branded_token_sha256` (a **hash/handle** only). It has **no field** for a raw subscription/proxy link, deep-link
payload, or QR payload. Persisted to `subscription_deliveries`, whose schema **deliberately has no raw-link column**
(test asserts no `url`/`link`/`deep_link`/`qr_payload`/`subscription_url` column exists).

## Link / deep-link / copy-link / QR behavior
- **Mode priority:** Hiddify App **deep link** → **copy-link** (branded) → **QR**. `primary_mode` is the first
  available; safe default is copy-link (a branded copy is always derivable once a token exists).
- **Deep link** is treated as secret — its presence is recorded as a boolean only; the payload is never stored/logged.
- **Copy-link** uses the **branded** link (below), not the raw Hiddify URL.
- **QR is PLANNED, not generated** (stdlib-only; no safe encoder without a risky dep). `qr_renderer.qr_plan()` returns
  `available=False, status="planned"`. When implemented later, QR must be built **in memory from the branded link at
  send time** and never persisted. This is documented honestly — no Gallery/Album behavior is claimed.

## Branded link rule
The only customer-facing link shape is **`https://sub.unseen.click/s/<opaque-token>`**, assembled **in memory at
send time** (`link_renderer.branded_link`) and **never persisted/logged**. Only the token's **SHA-256 handle** is
stored (`branded_token_sha256`); the raw opaque token is dropped after hashing. Raw Hiddify proxy/subscription links
(`hiddify://`/`vless://`/`ss://`/`hy2://`, `…/api/v2/…`, `…/all-configs…`) are **internal fallbacks only** — never the
main product link; `link_renderer.looks_like_raw_proxy_link` lets callers refuse to persist/log them, and
`subscription_delivery._guard_no_raw_link` enforces it before any DB write/audit.

## Hiddify output normalization
`hiddify_subscription_output.normalize(mocked_output)` accepts the verified output shapes (`all_configs`,
`me`/subscription metadata, protocol configs) **as an in-memory mock** and returns a `SubscriptionOutputSummary`:
`profiles_count`, `protocols` (engine names only — `hysteria2`/`shadowsocks`/`vless-reality`), `has_subscription_url`,
`has_deep_link`. The **raw output is inspected then discarded** — never logged, never returned; the summary contains no
link/UUID/QR/token. Bad input returns an empty summary (no crash).

## Notification / Telegram integration
`prepare_delivery` enqueues a NotificationService message (`channel=telegram`, `purpose=transactional`,
`payload_ref="delivery:sub:<id>"` — reference only, no body/link). The existing Phase 5 sender renders it via
`telegram_messages.render_payload` (`delivery:sub*` → the Burmese delivery text). `render_preview` produces a safe
Burmese-primary preview describing the available modes (deep link / copy link / QR-planned) with **no link/token/QR**.
**No live send** (Phase 5 gates remain closed).

## Dry-run / no-network guarantees
- The Hiddify output is a **mock** passed in by the caller/tests — nothing is fetched from de1.
- A test patches `urllib.request.urlopen` to throw and runs `prepare_delivery` end-to-end → proves **no network call**.
- No Telegram send (queue-only). CLIs run on a temp DB with mocked output and print sanitized summaries only.

## Tests and results
```
cd /opt/unseen-proxy && python3 -m unittest discover -s tests -p 'test_*.py'
```
**Result: 122 tests, OK** (107 prior + 15 new). New coverage: branded link shape + token handle (raw not recoverable);
redaction of branded/raw links; raw-proxy-link detection; mocked output → sanitized summary (no raw values; bad input
safe); QR honestly planned (not generated); mode priority (deep > copy > qr; safe default copy); `DeliveryPayload`
stores refs/flags only; branded token stored as **hash** not raw; row + audit contain **no** raw token/link; delivery
notification enqueued with `payload_ref` only; preview has no raw link; audit sanitized; persistence **refuses** a raw
link; **no DB column can hold a raw link**; `prepare_delivery` makes **no network call**. All Phase 4/5 tests still pass.

## Secret-safety result
No secrets in source/docs/tests. No raw subscription/proxy link, deep-link payload, QR payload, UUID, or token is
persisted or logged anywhere: the delivery row stores refs/flags + a token **hash**; audit details are sanitized; the
notification stores a `payload_ref` only; the output normalizer discards raw values. Mock fixtures use
`EXAMPLE`/`example.invalid` placeholders (not real links). New source filenames don't match the
`*secret*`/`*token*`/`*credential*` globs. Pre-commit scan passes.

## Known limits
- QR is **planned, not generated** (deep-link + copy-link cover delivery for now).
- The branded token issuance/rotation pipeline (real opaque tokens + the `sub.unseen.click` sidecar that resolves them)
  is a later phase — Phase 6 stores only the **handle** and assembles the link in memory.
- Output normalization is driven by **mocks**; the real shapes are exercised only once de1 is rebuilt + live.

## Live blockers (intentional)
- **No real Hiddify provisioning** — Phase 4C live path stays hard-disabled; output here is mocked.
- **No real Telegram send** — Phase 5 gates remain closed (queue-only).
- **de1 rebuild still required** before real Hiddify provisioning (leaked-key blocker, [PHASE4_PRELIVE_DE1_TUNING.md](PHASE4_PRELIVE_DE1_TUNING.md)).
- **Real-device FAST1/FAST2/Secure PASS pending** (`#TASK_for_Charles`).

## Risks / follow-ups
- When going live: build the `sub.unseen.click` sidecar (resolves the opaque token → fetches the real node sub in
  memory, `access_log off`), wire real token issuance/rotation, and add QR generation (in memory only) if a vetted
  encoder is approved. Enforce `_guard_no_raw_link` on every new persistence/log path.

## Exact next recommended task
**Phase 6 sidecar (gated) or Phase 7 (entitlement/region resilience):** build the subscription-delivery **sidecar**
boundary that resolves a branded opaque token to an in-memory node subscription (still dry-run/mock until de1 is
rebuilt and a real-device protocol PASS is recorded), or proceed to plan-based region/protocol resilience. Live
delivery stays Charles-gated behind the de1 rebuild + protocol PASS.

# SECURITY

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §31, §30A.5, §31A
> **Status:** Phase 1 skeleton — decided from plan

The non-negotiable security and secret-safety rules for UNSEEN PROXY. These are enforced in code review and in the agent's behavior; violating one is a defect.

## The 10 non-negotiable rules (§31)

1. **Never expose secrets.** No tokens, token hashes, subscription URLs, QR payloads, deep links containing tokens, API keys, panel admin paths, panel/admin credentials, Reality private keys/short-ids, or customer PII in logs, errors, audit entries, commits, chat output, or third-party calls. Print only **fingerprints** and **masked IPs**.
2. **Durable tokens are encrypted at rest** with `ACCESS_TOKEN_ENCRYPTION_SECRET`. Raw tokens are never stored; URLs/QRs are built in memory and never persisted.
3. **No third-party exfiltration.** Subscription URLs/tokens are never submitted to external services. Submitting a sub URL to an external "crypt" service counts as exfiltration and is hard-blocked. Any crypto/obfuscation is done locally or out-of-band.
4. **Do not hardcode business values.** Plans, prices, caps, durations, device counts, region lists, and protocol labels all come from the DB.
5. **Not all regions/protocols live by default.** Each is enabled explicitly after a node test.
6. **No risky protocol/routing changes without testing** on a disposable target first.
7. **Honest promises only.** Never tell users configs are impossible to copy/share. Lean on per-user tokens, caps, expiry, rotation, UA-filter, and leak monitoring.
8. **Least-privilege node API keys.** Panel admin paths and ports are not public; consider IP-allowlisting the web admin.
9. **`.env` files are `0600`, root-owned; secrets never enter git** (enforced by `.gitignore` + a pre-commit secret scan, §31A). Use `.env.example` with placeholder keys.
10. **Never fabricate a PASS.** Always verify artifacts exist on disk / endpoints actually return the expected status before reporting success. Fail closed and say so honestly when blocked.

## Secret-safety posture

- **Fingerprints + masked IPs only.** Sanitized-by-construction logging (§30.1): subscription/sidecar logs carry fingerprint + status + body length + UA class + masked IP prefix — never raw token/URL/body/full IP/PII.
- **Durable tokens encrypted at rest.** Encryption uses `ACCESS_TOKEN_ENCRYPTION_SECRET`; losing it makes tokens undecryptable (see [BACKUPS.md](BACKUPS.md)). Raw tokens are never stored.
- **No third-party exfiltration** of subscription URLs or tokens (rule 3).
- **Least-privilege node API keys** (rule 8); admin paths/ports stay non-public.
- **Never fabricate a PASS** (rule 10) — fail closed and report honestly when blocked.
- **Timezone clarity is a safety rule.** Business/customer dates use Myanmar Time (MMT, UTC+06:30, `Asia/Yangon`);
  technical UTC fields, if introduced later, must be explicitly labeled so they cannot be mistaken for subscription,
  payment, invoice, bot, portal, or admin business dates.
- **de1 node-domain/cert change (2026-06-16) preserved rule 1.** Setting `node-de.unseen.click` + its cert and
  verifying it emitted **only** HTTP status codes, domain names, byte sizes, and service states. The admin link/proxy
  path/admin UUID/API key, user UUIDs, Reality/WireGuard/private keys, subscription URLs, proxy links, and QR payloads
  stayed on the node — never printed or committed. Verification used a **disposable** user (`disposable-test-realdevice`,
  1 GB/1 day) only; `current.json` was backed up on-node before the change. de1 remains `status=test`. **Real-device
  import must use a disposable user's subscription under `node-de.unseen.click` with valid TLS — never the admin/terminal
  QR, never a raw-IP/sslip.io link.**
- **Subscription-output inspection stays sanitized (2026-06-16).** Diagnosing the Hiddify-App import failure required
  fetching the disposable user's subscription/all-configs; this was done with a **counts-only sanitizer** (byte sizes,
  line counts, and occurrence counts of host/loopback/port/protocol tokens — **no raw lines, links, configs, or QR
  printed**). Bodies were written to root-only `mktemp` files and **`shred -u`**'d afterward; nothing raw was staged or
  committed. The admin link/proxy path/UUIDs/keys stayed on the node. **Future nodes must inspect subscription output
  this way (runbook §5B) before any real-device test.**
- **Disclosed sanitization slips (2026-06-16, test node, not committed).** While diagnosing the `tunnel-per-resolver`
  parser error, two over-broad sanitized queries briefly printed secret values **to the operator terminal only (never to
  git):** (1) the **DNSTT keypair** (a value-dumping `jq` over config keys) and (2) the **disposable user's UUID** (a
  redirect `&user=<uuid>` query a path-only regex missed). **Remediation:** DNSTT was **disabled** (keys now unused; they
  live only in the node's root-only `current.json`); the exposed disposable **UUID was rotated** (delete+recreate). de1
  is a no-customer **test** node, so per standing guidance this is **not** a new leaked-key rebuild blocker. **Lesson
  (enforced in runbook §5B):** emit only counts/booleans — never value dumps — and sanitize **query-param** UUIDs
  (`&user=<uuid>`), not just path UUIDs. Config/secret-bearing renders go to root-only temp files and are `shred -u`'d.
- **Disposable profile pasted → rotated (2026-06-16).** Charles pasted disposable test-profile/config text (with client
  secret material) into chat for troubleshooting. That `disposable-test-realdevice` user was treated as **burned** and
  **rotated** (delete + recreate one fresh user). This is **not** a real-customer leak and **not** a de1 rebuild blocker:
  de1 is **test-only**, no real customers exist, the user was rotated, and **no committed file** ever held the material.
  All output inspection during the UNSEEN prune used **counts-only** sanitized scanners on root-only temp renders that
  were `shred -u`'d — no links/UUIDs/keys/raw configs printed or committed.

## Portal HTTP boundary (Phase 8C — local-only, verified by tests)

The local-only portal HTTP adapter enforces these rules in code (no public endpoint yet):

- **Sanitized access logs by construction** (`backend/access_log.py`): a log line carries
  `METHOD sanitized-path status masked-ip` only. `/s/<token>` → `/s/<redacted>`, query strings are dropped,
  and `Cookie`/`Set-Cookie`/`Authorization`/`X-Api-Key`/`X-Csrf-Token`/`Hiddify-API-Key` headers are dropped.
  UUIDs, proxy/subscription URIs, bot-token shapes, `/api/v2/` admin paths, and long opaque tokens are redacted.
- **Hardened session cookies** (`backend/portal_cookies.py`): HttpOnly + Secure + SameSite + Path=/ + Max-Age.
  The raw session id lives only in the cookie value; it is never logged or written to page source. Lookups are
  hash-backed (`portal_sessions`/`portal_access`).
- **CSRF foundation** (`backend/portal_csrf.py`): signed, constant-time-verified, expiring tokens for future
  POST routes; raw tokens are never logged or persisted. GET-only render routes are exempt by design.
- **Fail-closed rate limiting** (`backend/rate_limit.py`): repeated branded-token attempts are blocked; keys are
  token *fingerprints*, never raw tokens or paths.
- **Hardened response headers** (`backend/portal_middleware.py`): `nosniff`, `X-Frame-Options=DENY`,
  `Referrer-Policy=no-referrer`, restrictive CSP, `no-store` for private pages.
- **Dry-run sidecar** (`backend/sidecar_boundary.py`): verifies branded tokens hash-backed and returns safe
  placeholders; never fetches/persists live Hiddify subscription output.
- **No public deployment, no nginx/TLS, no systemd, no public bind** — the preview server is loopback-only and
  refuses `0.0.0.0`. See [PHASE8C_PORTAL_HTTP_DEPLOYMENT_BOUNDARY.md](PHASE8C_PORTAL_HTTP_DEPLOYMENT_BOUNDARY.md).

## Phase 4B secret-safety (service boundaries — verified by tests)

The Phase 4B backend slice ([PHASE4B_ACCOUNT_NOTIFICATION_BACKUP.md](PHASE4B_ACCOUNT_NOTIFICATION_BACKUP.md)) keeps
rules 1–2 by construction:

- **Account-link codes are stored hash-only.** `issue_link_code` returns the raw code once and stores **only its
  SHA-256 hash** (`account_link_tokens.code_hash`); the raw code is never persisted or logged. Validation is
  **reason-opaque** (unknown/expired/used are indistinguishable) — no information leak to a guesser.
- **The notification queue stores references, not bodies.** `outbound_messages.payload_ref` is a handle/template id;
  `last_error` is a sanitized reference. No raw message body, token, URL, or QR payload is stored.
- **Identity is internal.** The raw platform id is never the customer identity (only a `platform_accounts` lookup key);
  the public-facing id is the gap-safe `public_customer_code`.
- **Backups expose no values.** The online-backup manifest records **paths and check results only**; `.env` contents
  are never read or printed in this slice (`env_contents_backed_up: false`).
- **No new secret-named source files** — none of the Phase 4B modules match the `*secret*`/`*token*`/`*credential*`
  `.gitignore` globs; the pre-commit secret scan passes.

## Secret rotation (§30A.5)

A no-downtime rotation runbook exists for the two long-lived secret classes — `ACCESS_TOKEN_ENCRYPTION_SECRET` (re-encrypt token payloads old→new, bumping `token_storage_version`, both secrets held during transition) and node API keys (issue new least-privilege key, verify read-only probe, revoke old). Rotation is gated/latched (env latch + `--live --confirm`), backed up before and verified after. See [SECRET_ROTATION.md](SECRET_ROTATION.md).

## Secret-scan in git (§31A)

`.gitignore` plus a pre-commit hook scan staged changes for secret-shaped strings and block the commit if any are found. A committed secret is a **security incident**: rotate the exposed secret (§30A.5), don't just delete the commit. See [VERSION_CONTROL.md](VERSION_CONTROL.md).

## Hiddify-specific secret & exposure rules (Phase 3 audit)

> **Future node installs follow [HIDDIFY_NODE_INSTALL_RUNBOOK.md](HIDDIFY_NODE_INSTALL_RUNBOOK.md)** §6 (secret safety):
> admin link only in `/root/hiddify-<node>-admin.link` (`0600`); API verification emits only status codes / JSON key
> names / counts (never bodies); always `curl -o` to files + quote UA/headers; disposable test users only.

From the verified Hiddify model (see [PHASE3_HIDDIFY_AUDIT_PLAN.md](PHASE3_HIDDIFY_AUDIT_PLAN.md) /
[HIDDIFY_API_CONTRACT.md](HIDDIFY_API_CONTRACT.md)):

- **The API key IS the admin UUID.** Hiddify API v2 auth is `Hiddify-API-Key: <admin-UUID>` — the UUID is the
  credential. Treat it like any node API key (rule 8): `.env` by handle, least-privilege, never in DB/logs/git/chat.
- **Secret proxy paths.** The `<admin_proxy_path>` / `<user_proxy_path>` and the panel admin path are secret URL
  segments — `.env`-only, never logged or shown to customers (rule 1).
- **Firewall is Hiddify-managed (iptables) on the node.** On the DE node VPS, don't run a competing ufw/nft ruleset
  that fights it; verify SSH:22 survives from a second session post-install and keep a provider recovery path.
- **Install runs on the dedicated DE node VPS, not the Master** ([DECISIONS.md](DECISIONS.md) ADR-001 — co-location
  retired; the protected control plane stays Hiddify-free). Use the **supported Ubuntu-22.04 host installer**; a fresh
  node VPS is disposable, so the host-on-control-plane snapshot concern no longer applies. **Reality private
  keys/short-ids** generated by Hiddify remain secrets (rule 1).
- **Master↔node SSH key** is least-privilege, private half on the Master only (`0600`), never in git. Verified
  working to `de1` as root (key-only) on 2026-06-15.
- **`de1` hardening TODO (post-install, 2026-06-16):** Hiddify v12.3.3 is installed; `de1` has **ufw active** (only
  22/tcp explicitly allowed; Hiddify manages its own iptables for proxy ports — **verify coexistence & that SSH stays
  open**). **Password SSH login is still enabled** → disable it (key access confirmed). The Hiddify admin link /
  admin_proxy_path / admin-UUID (API key) / Reality keys are **secrets** — admin link kept only at
  `/root/hiddify-de1-admin.link` (0600), never in git/logs. Lock 4 GB RAM before live use. See
  [PHASE3_DE1_HIDDIFY_LIVE_VERIFY.md](PHASE3_DE1_HIDDIFY_LIVE_VERIFY.md).
- **Operational lesson (recorded):** never set a restrictive `umask` (e.g. 077) when launching third-party installers
  — it propagates into created files/dirs (and package caches), producing unusable perms. Use the default 022.
- **Secret-handling incident (2026-06-16, disclosed):** during de1 API debugging, an **unquoted User-Agent with spaces**
  mis-aligned `curl` args so a response body printed to the terminal, exposing the Hiddify **default** user's ed25519
  private key + WireGuard keys + uuid. **Not committed to git** (terminal only); **no-customer `test` node**. Fixes:
  (1) **always write API response bodies to files** (`-o`), never let them hit stdout; (2) **always quote** UA/headers;
  (3) before de1 goes live, **regenerate the default-user/server secrets** (or rebuild the node). Recorded so the
  pattern isn't repeated when the orchestrator handles real per-customer keys.
- **✅ Leaked-key incident RESOLVED (Phase 9, 2026-06-16):** de1 was **rebuilt fresh** (provider reinstall) and Hiddify
  v12.3.3 cleanly reinstalled, **regenerating all default-user/server secrets** — the previously exposed keys are gone.
  SSH re-hardened (**password auth disabled, key-only**, port unchanged, verified). API re-verification followed the
  same secret-safe discipline (bodies to files; only status codes / JSON key names / counts emitted; admin
  link/proxy-path/UUID/keys never printed). `leaked_key_rebuild_pending` cleared in code/seed. de1 stays `status=test`.
  See [PHASE9_DE1_REBUILD_FRESH_HIDDIFY.md](PHASE9_DE1_REBUILD_FRESH_HIDDIFY.md).
- **Master minimalism / attack-surface** ([DECISIONS.md](DECISIONS.md) ADR-003): the Master runs only control-plane
  services; packages installed solely for the retired co-location path (notably the now-unused **Docker engine**) are
  cleanup candidates to be removed in a future audited task — keeping the protected control plane minimal.
- **Node-facts probe is read-only** ([DECISIONS.md](DECISIONS.md) ADR-002): the preflight probe (future
  `scripts/node_preflight_probe.sh`) **only reads** node state over SSH — it must **never mutate the node** and
  **never print/commit secrets** (no admin link/UUID/proxy paths/keys); results recorded sanitized. Don't trust
  manually-entered specs for security/role decisions — verify by detection.

## de1 pre-live hardening + leaked-key decision (Phase 4, 2026-06-16)

See [PHASE4_PRELIVE_DE1_TUNING.md](PHASE4_PRELIVE_DE1_TUNING.md).

- **SSH is now key-only on de1.** `PasswordAuthentication no` / `KbdInteractiveAuthentication no` /
  `PubkeyAuthentication yes` via `/etc/ssh/sshd_config.d/99-unseen-proxy-hardening.conf`; the cloud-init
  `PasswordAuthentication yes` (which sorts before `99-` and would otherwise win) was neutralized and
  `ssh_pwauth: false` set so cloud-init won't re-enable it. **Root key login retained** (`without-password`);
  SSH port unchanged. Verified: fresh key login works; a password-only attempt is **refused** (`publickey` only).
- **Node host key pinned** in the Master `known_hosts` (`ED25519 SHA256:lsD6hjAKLOdH/jqQZ28Ps0/1NLW5fW6/aV+nuwxn3gg`)
  → future connections use `StrictHostKeyChecking=yes`.
- **Leaked default-user/server keys → `REBUILD_REQUIRED_BEFORE_LIVE`.** Rule 10 (no fabrication) + rule 6 (no risky
  improvisation): Hiddify offers no safe surgical rotation of the leaked default-user/server protocol secrets
  (`reset-owner-password` is admin-password-only; reinstall is destructive). The leaked secrets are treated as
  compromised; the node must be **rebuilt** before any live/real provisioning (regenerates all server/user secrets).
  Dry-run work may continue on the test node. **No secret value was printed or committed during this task.**

## de1 real-device protocol diagnosis secret-safety (2026-06-16)

The real-device connectivity diagnosis ([PHASE9_DE1_REBUILD_FRESH_HIDDIFY.md](PHASE9_DE1_REBUILD_FRESH_HIDDIFY.md)
addendum) was **secret-safe by construction**:

- The sanitized sing-box scanner and API-health probe ran **on the node** and emitted **only** counts, booleans, HTTP
  status codes, byte sizes, and non-secret port numbers — **never** outbound bodies, subscription/proxy links, user or
  admin UUIDs, Reality/private keys, Hysteria2/SS passwords, or QR payloads. The config was rendered **in-memory** (not
  written to disk); user display labels were emitted only through an allowlist filter that redacts UUID-shaped values.
- The **admin link was used internally on-node only** (read from `/root/hiddify-de1-admin.link`, `0600`); its host/
  proxy_path/UUID were **never printed** — the probe reported status codes alone. All temporary helper scripts on the
  node were **removed** after use.
- All log inspection was piped through a **redactor** (strips UUIDs, `/s/<token>`, auth headers, long base64 blobs).
- **No node change was made** (HOLD decision); de1 stays `status=test`; `realdevice_protocol_test_pending` remains.
- Repo changes are **docs + SOURCE_OF_TRUTH only**; pre-commit secret scan run before commit.

## Phase 4C secret-safety (dry-run provisioning — verified by tests)

The Phase 4C orchestration ([PHASE4C_DRY_RUN_PROVISIONING.md](PHASE4C_DRY_RUN_PROVISIONING.md)) keeps rules 1–2 by
construction: the provisioning plan summary and the **sanitized Hiddify mutation intent** carry no API key, admin path,
user UUID, subscription URL, proxy link, or QR payload (relative `/user/` path + GiB→GB number only). Access profiles
store a **placeholder token hash** (no raw token/URL/UUID in dry-run). Delivery notifications store a `payload_ref`
only. Audit details carry internal ids/quotas only. **Live provisioning is hard-disabled** and refuses even with the
env latch + `--live --confirm` (the leaked-key rebuild blocker is one of the always-present refusal reasons).

## Phase 5 secret-safety (Telegram bot foundation — verified by tests)

The Phase 5 bot foundation ([PHASE5_TELEGRAM_BOT_FOUNDATION.md](PHASE5_TELEGRAM_BOT_FOUNDATION.md)) keeps rules 1 & 9
by construction:

- **Bot token is read by env NAME only** (`TELEGRAM_BOT_TOKEN`), never stored in a public field, never logged, and
  **redacted** in `repr`/fingerprint (`tg:<botid>:<redacted>`). It is never committed (real value lives in `.env` on
  the Master only). The adapter is **dry-run** and **refuses live sends** (`config.PHASE5_LIVE_SEND_DISABLED`).
- **Admin Telegram ids are env-driven** (`ADMIN_TELEGRAM_IDS`, fallback `TELEGRAM_ADMIN_IDS`) — **no hardcoded id**; the
  full list is never logged/rendered (only a sanitized `admin_count`); placeholder values are treated as "no admins".
- **No secrets in bot copy or flows** — messages/plan/status/admin summaries carry no token, UUID, subscription URL,
  proxy link, QR payload, admin path, or payment ref. Notifications store a `payload_ref` only. Malformed updates and
  errors yield safe Burmese replies — no stack traces, no secrets.

## Phase 5 transport secret-safety (gated; verified by tests)

The Phase 5 transport layer ([PHASE5_TELEGRAM_TRANSPORT_FOUNDATION.md](PHASE5_TELEGRAM_TRANSPORT_FOUNDATION.md)) keeps
rules 1, 9 & 10 by construction:

- **Bot token never leaks.** `TelegramTransport` stores the token name-mangled (no public field), never logs it, and
  redacts it in `repr`/fingerprint. The Bot API URL embeds the token (`/bot<token>/<method>`) and is built **only**
  inside `_request` — never logged, returned, or placed in an error/repr (errors carry the method name only). A test
  asserts the token and token-URL never appear in `repr` or request params.
- **Live is fail-closed (double gate).** `runtime_gates` requires the exact env latch `"1"` **and** explicit
  `--live-send`/`--live-poll` + `--confirm`; anything missing/invalid refuses with sanitized blocker reasons. Default
  is dry-run/no-network. Even when gated open, tests inject a **mock** transport — no real network in the suite.
- **Queue stores references only.** The sender renders from `outbound_messages.payload_ref` (a template key) — no raw
  body, link, token, or QR is ever stored or sent. Admin ids remain env-driven and unlogged.

## Phase 6 secret-safety (subscription delivery — verified by tests)

The Phase 6 delivery foundation ([PHASE6_SUBSCRIPTION_DELIVERY_FOUNDATION.md](PHASE6_SUBSCRIPTION_DELIVERY_FOUNDATION.md))
upholds rules 1 & 2:

- **No raw links/tokens/QR persisted or logged.** `subscription_deliveries` has **no column** for a raw
  subscription/proxy link, deep-link payload, or QR payload (test-asserted). Only safe refs/flags + the branded token
  **SHA-256 handle** are stored. Audit details and the notification `payload_ref` are sanitized references only.
- **Branded link is in-memory only.** `https://sub.unseen.click/s/<token>` is assembled at send time and never
  persisted/logged; `link_renderer.redact_link` produces a safe label, and `subscription_delivery._guard_no_raw_link`
  refuses to persist/log anything matching a raw proxy/subscription link shape.
- **Hiddify output is mocked + discarded.** `hiddify_subscription_output.normalize` extracts non-secret facts
  (counts/engine names/booleans) and drops the raw output — never logged or returned.
- **QR is honestly reported as planned** (not generated) — no QR payload exists to leak.

## Phase 7 secret-safety (entitlement + node resilience — verified by tests)

The Phase 7 resolvers ([PHASE7_ENTITLEMENT_NODE_RESILIENCE.md](PHASE7_ENTITLEMENT_NODE_RESILIENCE.md)) emit only
sanitized facts — region/protocol codes, node statuses, health, counts, and reason codes from a fixed vocabulary.
**No node IP, hostname, API key, admin path, UUID, link, or QR** appears in any resolver output, provisioning-plan
summary, audit row, or customer-facing message (test-asserted, including the de1 IP). The data-driven
`node_live_blockers.detail` is a sanitized note. Customer availability copy (Burmese) names only public product facts
(DE/US/SG, protocol display labels) — never internal inventory. Health is derived from `node_alerts` rows; no real
node is contacted in this phase.

## Phase 7 health-monitor secret-safety (read-only probes — verified by tests)

The Phase 7 monitor ([PHASE7_HEALTH_MONITOR_FOUNDATION.md](PHASE7_HEALTH_MONITOR_FOUNDATION.md)) is read-only and
sanitized by construction:

- **Probes are public-only and payload-free.** The opt-in `PublicTcpProber` does read-only TCP connects to 22/80/443
  and an optional HTTP HEAD to the **public root** — it never touches the secret admin path, never sends a proxy
  payload, and never uses a third-party tester. UDP/Hysteria2 stays `unknown`.
- **Raw errors are never stored.** `probe_sanitizer` maps any exception to a reason code
  (`probe_timeout`/`probe_error_sanitized`); a host/URL/IP in the message is discarded (test-asserted).
- **Metrics/alerts carry no secrets.** Only numbers + sanitized check names + levels — no admin link, API key, UUID,
  subscription/proxy link, or QR. Customer availability copy has no IP/host/secret.
- **No daemon / no systemd / no node modification / no Hiddify or Telegram call.** Writes happen only when a CLI is run
  with `--write-metrics` against an explicit local/test DB.

## Phase 8 portal secret-safety (render-only — verified by tests)

The portal foundation ([PHASE8_WEB_PORTAL_FOUNDATION.md](PHASE8_WEB_PORTAL_FOUNDATION.md), [PORTAL.md](PORTAL.md))
keeps the customer web surface dry-run and secret-safe:

- **No public endpoint exists.** The portal returns HTML strings/`PortalResponse` objects only; no web server, nginx/TLS,
  systemd unit, live auth, Hiddify call, or Telegram send/poll is configured.
- **All dynamic HTML is escaped.** Plan names, statuses, dates, region labels, and customer/subscription labels are
  passed through `html.escape`; tests inject markup-shaped plan/status values and verify they render as text.
- **Identity stays public-code based.** The dashboard shows `customers.public_customer_code`; raw platform ids and
  `platform_accounts` values are never displayed.
- **Delivery stays placeholder-only.** The branded link renders as `https://sub.unseen.click/s/<opaque-token>` and
  `/s/<opaque-token>` does not resolve anything. No raw subscription/proxy link, QR payload, admin path, UUID-shaped
  value, node IP/hostname, or raw opaque token appears in rendered HTML (test-asserted).
- **Assets are local.** CSS is embedded from `backend/portal_static.py`; no CDN, external font, image, or script
  reference is used.
- **Phase 8A preview export stays local and ignored.** `bin/portal_preview_export.py` writes only under the repo's
  git-ignored `tmp/` directory, refuses outside paths, and scans rendered HTML for forbidden raw Hiddify/proxy URL
  shapes and UUID-shaped values before writing. Generated previews were additionally scanned and are not staged.
- **Phase 8B auth/session primitives are hash-only.** `portal_access_tokens` and `portal_sessions` store only hashes;
  raw portal tokens and raw session ids exist only in memory for immediate dry-run handoff. Verification uses
  constant-time comparison. Private portal pages require a `PortalSessionContext`; invalid/expired/revoked `/s/` tokens
  render safe pages without echoing the token. Audit rows carry sanitized ids/reasons only.
- **Timestamp audit is local and sanitized.** `bin/timezone_audit.py` scans code/docs for timestamp risk patterns and
  prints file/path summaries only; it does not read databases, contact services, or emit customer/product data.

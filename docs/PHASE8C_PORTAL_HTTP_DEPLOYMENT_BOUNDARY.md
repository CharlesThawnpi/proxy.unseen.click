# PHASE 8C — Portal HTTP Deployment Boundary (gated, local-only)

> **Date:** 2026-06-16T08:24Z UTC — 2026-06-16 14:54 MMT (Myanmar Time, UTC+06:30, `Asia/Yangon`)
> **Status:** Foundation complete — local-only, dry-run. **No public deployment, no server running.**

## Scope

Build the portal HTTP adapter / deployment boundary **without exposing it publicly**. This phase
adds the request/response abstraction, secure-cookie middleware, CSRF foundation, rate-limit
foundation, access-log sanitizer, and a dry-run subscription sidecar boundary, plus local-only
smoke/preview CLIs. It deliberately does **not** start a persistent service, configure nginx/TLS,
bind a public interface, or expose a public endpoint.

This is a foundation: the future web server (or the loopback preview CLI) wraps `portal_http`,
which in turn wraps the existing render-only `portal_routes.render_route` from Phase 8/8A/8B.

## Files created/changed

**Created (backend):**
- `backend/portal_http.py` — HTTP request/response abstraction + `PortalHttpApp` router.
- `backend/portal_middleware.py` — security headers + cookie→session-context middleware.
- `backend/portal_cookies.py` — cookie builder/parser helpers.
- `backend/portal_csrf.py` — signed, stateless CSRF token foundation.
- `backend/rate_limit.py` — in-memory fixed-window rate-limit foundation.
- `backend/access_log.py` — access-log sanitizer + policy.
- `backend/sidecar_boundary.py` — dry-run `sub.unseen.click` sidecar boundary.

**Created (CLIs, local-only):**
- `bin/portal_http_smoke.py` — in-memory HTTP-adapter smoke (temp DB; no socket).
- `bin/portal_local_preview_server.py` — loopback-only preview server (operator tool; refuses public bind).
- `bin/sidecar_boundary_smoke.py` — sidecar boundary smoke (temp DB; no live Hiddify).

**Created (tests):**
- `tests/test_portal_http.py` — 26 tests covering routing, cookies, CSRF, rate limit, access-log
  sanitizer, sidecar boundary, preview-server safety, and smoke-CLI secret-safety.

**Docs updated:** `docs/PORTAL.md`, `docs/SECURITY.md`, `docs/DEPLOYMENT.md`, `docs/CURRENT_STATUS.md`,
`docs/CHANGELOG.md`, this file, and regenerated `SOURCE_OF_TRUTH.md`.

## HTTP adapter behavior

- `HttpRequest` carries `method`, `path`, parsed `query`, `headers`, parsed `cookies`, `body`, and
  an optional `remote_addr`. `HttpRequest.build(method, target, ...)` parses the target into path +
  query and extracts cookies from the `Cookie` header.
- `HttpResponse` carries `status_code`, `headers`, `body`, and `content_type`.
- `PortalHttpApp.handle(request)` routes against a strict **allowlist** and wraps
  `portal_routes.render_route`. Everything off-list renders the safe `not-found` page (the unknown
  path is never echoed back).
  - Public (no session): `GET /`, `GET /plans`, `GET /help`, `GET /expired`, `GET /not-found`.
  - Private (session required): `GET /dashboard` → dashboard; `GET /subscription` → the customer's
    most recent subscription detail. No verified session → 401 auth-required page.
  - Branded: `GET /s/<opaque-token>` → resolver (rate-limited); raw token never logged.
  - Non-GET/HEAD → 405.
- No socket is opened and no network is required; all 26 tests run with `socket.socket` patched to
  fail.

## Cookie/session middleware behavior

- `portal_cookies.build_session_set_cookie(raw)` builds a hardened `Set-Cookie`: **HttpOnly +
  Secure + SameSite (Lax/Strict) + Path=/ + Max-Age**. `build_clear_session_cookie()` expires it.
- `portal_cookies.parse_cookie_header()` / `session_id_from_cookie_header()` parse inbound cookies.
- `portal_middleware.session_context_from_cookies()` reads the session cookie, hashes it, and
  verifies it via `portal_auth`/`portal_sessions` (hash-backed). The raw session id never leaves
  the call, is never logged, and never reaches page source.
- `portal_middleware.security_headers(private=...)` attaches `X-Content-Type-Options=nosniff`,
  `X-Frame-Options=DENY`, `Referrer-Policy=no-referrer`, a restrictive `Content-Security-Policy`,
  `Cross-Origin-Opener-Policy=same-origin`, and `Cache-Control: no-store` for private pages.

## CSRF foundation behavior

- `portal_csrf` mints a signed, self-contained token `nonce.exp.sig` where
  `sig = HMAC-SHA256(key, "nonce.exp")`. Verification recomputes the signature in **constant time**
  (`hmac.compare_digest`) and rejects tampered, malformed, wrong-key, expired, and absent tokens.
- Expiry is stamped from the **MMT clock helper** (`backend.timezone`), so the whole project shares
  one notion of "now"; `now` is injectable for deterministic tests.
- GET-only render routes do **not** carry CSRF (documented exemption). Future POST routes (login,
  plan selection, payment confirmation) MUST require a valid CSRF token before mutating state.
- The raw token is never logged or persisted; `portal_csrf.redact()` emits only a non-reversible
  marker.

## Rate-limit behavior

- `rate_limit.RateLimiter` is an in-memory fixed-window counter with a refreshing block window.
  Policy **fails closed**: the attempt that crosses the threshold is itself blocked, and the block
  timer refreshes on every further attempt so a persistent attacker stays blocked.
- `rate_limit.branded_token_limiter()` is the default policy (5 attempts / 60s window / 300s block)
  for the `/s/<opaque-token>` resolver and future login/session endpoints.
- Keys are derived via `rate_limit.safe_key(raw_token)` = `scope:fingerprint` — the **raw token is
  never used as a key and never logged**.
- At the HTTP layer, repeated branded-token attempts past the threshold return **429** with
  `Retry-After`. Tests prove threshold + window-rollover behavior.
- No production daemon/store yet; a multi-worker deployment will need a shared store.

## Access-log sanitizer policy

- `access_log.sanitize_path()` redacts `/s/<token>` → `/s/<redacted>` and **drops query strings
  entirely** (the boundary logs no GET query params).
- `access_log.sanitize_headers()` **drops** `Cookie`, `Set-Cookie`, `Authorization`,
  `Proxy-Authorization`, `X-Api-Key`, `X-Auth-Token`, `X-Csrf-Token`, `Hiddify-API-Key`
  (→ `<redacted>`) and redacts secret-shaped values from the rest.
- `access_log.redact_text()` redacts UUIDs, proxy/subscription URIs (`vless|vmess|trojan|ss|hy2|
  hysteria2|hiddify://…`), Telegram-bot-token shapes, `/api/v2/…` admin paths, and long opaque
  token runs.
- `access_log.redact_ip()` masks client IPs (`203.0.x.x`) for customer-facing/exported logs.
- `format_access_event()` emits one sanitized line: `METHOD sanitized-path status ip`.
- Tests assert logs never contain raw tokens, cookies, auth headers, query tokens, UUIDs, or proxy
  links.

## Sidecar boundary behavior

- `sidecar_boundary.handle_branded(conn, raw_token)` verifies the branded token **hash-backed** via
  `portal_access.verify_token` (no session minted, **no Hiddify call**) and returns a safe
  placeholder document. `fetched_live` is always `False` in Phase 8C.
- Invalid → 404, expired/revoked → 410, valid → 200 placeholder. Optional rate limiter supported.
- `sanitized_access_line()` logs `GET /s/<redacted> status ip` — the raw token is never an input.
- The real node-subscription fetch is intentionally absent; raw Hiddify output is never persisted.

## Local-only / no-public-deployment guarantees

- No module opens a socket or starts a server on import or during dispatch.
- `bin/portal_local_preview_server.py`:
  - starts **nothing** unless `--serve-local` is passed (default run prints guidance, exits 0);
  - binds **only** a loopback host (`127.0.0.1`/`::1`/`localhost`) and **refuses** `0.0.0.0` (exit 2)
    until a future, separate task approves a public bind;
  - uses a fresh temp DB; creates no systemd unit, no nginx config, no TLS.
- The HTTP adapter is exercised entirely in-memory by tests and smokes.

## Tests and results

- New module `tests/test_portal_http.py`: **26 tests** — all PASS.
- Full suite: **224 tests PASS** (198 prior + 26 new). `python3 -m unittest discover -s tests -p 'test_*.py'`.
- Smokes: `bin/portal_http_smoke.py` and `bin/sidecar_boundary_smoke.py` print `SMOKE_OK` and are
  asserted secret-free; `bin/portal_local_preview_server.py` does not autostart and refuses public bind.

## Secret-safety result

- No raw portal tokens, raw session ids, raw CSRF tokens, bot token, admin IDs, Hiddify
  link/path/API key, UUIDs, subscription/proxy URLs, QR payloads, or payment refs are printed,
  logged, or committed. Cookie values and CSRF tokens exist only in memory / in the cookie value
  position. Access logs are sanitized by construction. Pre-commit secret scan run before commit.

## Known limits

- In-memory rate limiter is process-local (single request loop) — a multi-worker production
  deployment needs a shared store.
- CSRF signing key is per-process/in-memory; a real deployment must source it from secret config.
- The preview server is an operator dev tool, not a hardened server (no TLS, no concurrency tuning).
- `/subscription` resolves the customer's most recent subscription only (no list/selection UI yet).

## Live blockers

- **No public deployment yet** — local-only boundary.
- **No systemd / nginx / TLS** configured.
- **No real cookie/session service** live.
- **No live subscription resolution** — sidecar returns placeholders only.
- **No live Hiddify provisioning.**
- **de1 rebuild still required** before real provisioning (clears `leaked_key_rebuild_pending`),
  plus a real-device FAST1/FAST2/Secure PASS. de1 stays `status=test`.

## Risks / follow-ups

- Decide the production rate-limit store (shared) and CSRF key source (secret config) before any
  public bind.
- Public-bind enablement, nginx/TLS, and systemd are each a **separate, gated** task.
- The sidecar's live Hiddify fetch + streaming is a separate task, gated on de1 rebuild + PASS.

## Exact next recommended task

**de1 rebuild + real-device FAST1/FAST2/Secure verification** (clears `leaked_key_rebuild_pending`,
the standing live blocker). Alternatively, a separately-gated **public-deployment task** (nginx/TLS
+ systemd + public-bind approval for the portal HTTP adapter and `sub.unseen.click` sidecar) — but
that must not precede the de1 rebuild, since live provisioning stays blocked until then.

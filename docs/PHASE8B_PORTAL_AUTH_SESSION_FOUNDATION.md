# PHASE 8B — PORTAL AUTH / SESSION FOUNDATION

> **Date/time UTC:** 2026-06-16T07:13:43Z  
> **Result:** PASS — hash-only portal token/session foundation; render-only, no server.

## Scope

Built the customer-safe portal access/session foundation for future portal deployment. This phase adds secure opaque
portal tokens, hash-only session helpers, a branded `/s/<opaque-token>` resolver boundary, route guards for private
portal pages, sanitized auth audit rows, tests, and dry-run CLIs. It does not expose a public endpoint or enable real
customer login.

## Files Created / Changed

- Created `backend/migrations/0006_phase8b.sql`
- Created `backend/portal_tokens.py`
- Created `backend/portal_access.py`
- Created `backend/portal_sessions.py`
- Created `backend/branded_link_resolver.py`
- Created `bin/portal_auth_smoke.py`
- Created `bin/portal_token_dry_run.py`
- Created `tests/test_portal_auth.py`
- Updated `backend/portal_auth.py`
- Updated `backend/portal_routes.py`
- Updated `backend/portal_app.py`
- Updated `backend/portal_viewmodels.py`
- Updated portal dry-run CLIs to pass synthetic session context.
- Updated docs and regenerated `SOURCE_OF_TRUTH.md`.

## Portal Token Model

- `portal_tokens.generate_opaque_token()` uses secure randomness.
- `portal_access.issue_token()` returns the raw token once in memory and stores only `token_hash`.
- Token verification computes the hash and uses constant-time comparison.
- Tokens support `expires_at`, `revoked_at`, and `status`.
- Redaction/fingerprint helpers exist for safe smoke output. Raw tokens are not logged, rendered, or persisted.

## Branded `/s/<opaque-token>` Resolver Behavior

`backend/branded_link_resolver.py` resolves `/s/<opaque-token>` by hashing the raw token and checking
`portal_access_tokens`.

- Valid token: creates a dry-run portal session row and renders a safe "subscription ready" page.
- Unknown token: safe not-found page.
- Expired/revoked token: safe expired page.
- Literal `/s/<opaque-token>` remains a placeholder route for local preview.
- No raw token, token hash, session id, UUID, proxy link, QR payload, or private data is rendered.

## Session Helper Behavior

- `portal_sessions.create_session()` stores only `session_hash`; raw session id is returned only in memory.
- `portal_sessions.verify_session()` supports valid/unknown/expired/revoked outcomes with constant-time comparison.
- `portal_sessions.revoke_session()` records a sanitized revocation audit row.
- Cookie helper output models future attributes: `HttpOnly`, `Secure`, `SameSite=Lax|Strict`, `Path=/`.
- No live cookie is set because no HTTP server exists in this phase.

## Access-Control Behavior

- Public pages remain public: `/`, `/plans`, `/help`, plus status/error pages.
- Private pages (`/customer/status`, `/subscriptions/<id>`) require a `PortalSessionContext`.
- Render-only preview/smoke tools pass a synthetic session context against temp DB sample data.
- A session for another customer cannot view someone else's subscription detail; it receives a safe not-found page.
- Customer-facing identity remains `public_customer_code`; platform ids are not shown.

## Schema / Migration Behavior

Additive migration `0006_phase8b.sql` creates:

- `portal_access_tokens`
- `portal_sessions`

Both tables store only hashes/handles plus FK references, purpose/status, created/expiry/revocation timestamps, and
safe indexes. Migration re-run is idempotent through the existing migration runner and FK integrity is covered by tests.

## Security / Escaping Result

- Existing portal HTML escaping remains in place.
- Auth views render no raw token/session/hash values.
- Audit rows carry sanitized ids/reasons only; no raw tokens, raw session ids, session cookies, UUIDs, links, QR data, or
  private customer data.
- Smoke CLIs print only redacted token labels/fingerprints and status summaries.

## Dry-Run / No-Server Guarantees

- No web server started.
- No systemd unit created or enabled.
- No nginx/TLS/public endpoint configured.
- No real portal login/auth against production DB.
- No real customer portal session created.
- No Hiddify API call, live subscription fetch, Hiddify user creation, or node mutation.
- No Telegram send/poll/sender started.
- CLIs use a fresh temp DB by default.

## Tests And Results

- `python3 -m unittest discover -s tests -p 'test_portal*.py'` — 28 PASS.
- `python3 -m unittest discover -s tests -p 'test_migrations_schema.py'` — 3 PASS.
- `python3 bin/portal_auth_smoke.py` — PASS.
- `python3 bin/portal_token_dry_run.py` — PASS.
- Full suite result after Phase 8B: 191 PASS.

## Secret-Safety Result

Token/session tests assert raw token/session values are absent from DB rows and rendered HTML. Generated preview HTML and
auth smoke output were checked for raw Hiddify/proxy link shapes, UUID-shaped values, node hostnames, raw tokens, and
private sample ids. No generated preview files or runtime DB files were committed.

## Known Limits

- No public deployment.
- No real cookie/session service yet.
- No live `/s/<opaque-token>` resolution against Hiddify output.
- No live Hiddify provisioning.
- No QR generation.
- No admin portal.

## Live Blockers

- No public deployment yet.
- No real cookie/session service yet.
- No live subscription resolution.
- No live Hiddify provisioning.
- de1 rebuild still required before real provisioning.

## Risks / Follow-Ups

- Future live portal must add HTTP middleware, CSRF/session-hardening review, rate limiting, access logging policy, and
  production cookie setting.
- Token issuance must be wired to a trusted channel handoff only after live bot/sidecar gates are approved.
- Session and token retention/cleanup policy is still future work.

## Exact Next Recommended Task

Design the real portal deployment boundary before any public exposure: HTTP adapter, cookie-setting middleware,
rate limits, access logging, `/s/` live-resolution sidecar behavior, and operational runbook. Keep live provisioning
blocked until de1 is rebuilt and real-device FAST1/FAST2/Secure PASS is recorded.


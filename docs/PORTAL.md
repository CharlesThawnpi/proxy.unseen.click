# PORTAL

> **Status:** Phase 8C foundation — render-only + local-only HTTP adapter/middleware boundary, dry-run.

The customer portal foundation is a stdlib-only HTML renderer under `backend/portal_*`.
It is not a running service and has no real login yet. Phase 8C adds a local-only HTTP
deployment boundary (request/response abstraction, cookie/CSRF/rate-limit/access-log helpers,
and a dry-run subscription sidecar) — still no public endpoint, no server, no TLS.

## Timezone

Portal-visible subscription start/end, payment/order, invoice/receipt, and support dates use Myanmar Time (**MMT**,
UTC+06:30, `Asia/Yangon`). Current dry-run subscription, payment approval, token, and session service writes format
app-created timestamps through `backend.timezone`; preview pages label subscription dates as MMT.

## Boundary

- `backend/portal_app.py` exposes `render(conn, path, session_context=None)`.
- `backend/portal_routes.py` maps dry-run route shapes to `PortalResponse` objects.
- `backend/portal_viewmodels.py` reads DB-backed plans, subscriptions, delivery flags, and Phase 7 availability.
- `backend/portal_templates.py` escapes dynamic HTML and renders compact responsive pages.
- `backend/portal_static.py` embeds local CSS only; no CDN, fonts, images, or scripts.
- `backend/portal_auth.py` provides render-only `PortalSessionContext` helpers.
- `backend/portal_tokens.py`, `portal_access.py`, `portal_sessions.py`, and `branded_link_resolver.py` provide
  hash-only access/session primitives with MMT-aware service-created timestamps.

### HTTP deployment boundary (Phase 8C — local-only)

- `backend/portal_http.py` — `HttpRequest`/`HttpResponse` abstraction + `PortalHttpApp` router wrapping
  `render_route` behind a strict route allowlist (off-list → safe not-found; unknown path never echoed).
- `backend/portal_middleware.py` — hardened security headers + cookie→`PortalSessionContext` middleware
  (hash-backed; raw session id never leaves the call).
- `backend/portal_cookies.py` — hardened `Set-Cookie` builder (HttpOnly+Secure+SameSite+Path+Max-Age) + parser.
- `backend/portal_csrf.py` — signed, constant-time, expiring CSRF token foundation for future POST routes.
- `backend/rate_limit.py` — in-memory fail-closed fixed-window limiter (default: branded-token resolver policy).
- `backend/access_log.py` — access-log sanitizer (redacts `/s/<token>`, cookies, auth headers, query tokens,
  UUIDs, proxy links, bot/Hiddify secrets; masks client IP).
- `backend/sidecar_boundary.py` — dry-run `sub.unseen.click` sidecar: verifies branded token (hash-backed),
  returns safe placeholder, **never** fetches live Hiddify output.
- See [PHASE8C_PORTAL_HTTP_DEPLOYMENT_BOUNDARY.md](PHASE8C_PORTAL_HTTP_DEPLOYMENT_BOUNDARY.md).

## Pages

- `/` landing/home placeholder.
- `/plans` DB-driven plan table.
- `/customer/status` customer dashboard using `public_customer_code`; requires session context.
- `/subscriptions/<id>` subscription snapshot/status detail; requires matching session context.
- `/s/<opaque-token>` branded-link boundary; literal placeholder stays preview-only, real synthetic tokens resolve
  through hash lookup and create a dry-run session row.
- `/help`, `/unavailable`, `/degraded`, `/expired`, `/not-found`.

## Dry-Run Tools

- `python3 bin/portal_smoke.py`
- `python3 bin/portal_render_dry_run.py --page subscription --out tmp/portal-preview-single/subscription.html`
- `python3 bin/portal_preview_export.py --out-dir tmp/portal-preview`
- `python3 bin/portal_auth_smoke.py`
- `python3 bin/portal_token_dry_run.py`
- `python3 bin/portal_http_smoke.py` — in-memory HTTP-adapter routing/sanitization smoke (no socket).
- `python3 bin/sidecar_boundary_smoke.py` — sidecar boundary smoke (no live Hiddify).
- `python3 bin/portal_local_preview_server.py --serve-local` — **loopback-only** operator preview
  (refuses public bind; starts nothing without `--serve-local`; no systemd/nginx/TLS).

Both default to a fresh temp DB, seed sample data, render HTML, and exit. They do not start a server,
read production DB by default, generate real tokens, fetch Hiddify output, or send Telegram messages.
Output files are intentionally restricted to the repo's git-ignored `tmp/` tree.

## Local Preview Artifacts

For visual review, run:

`python3 bin/portal_preview_export.py --out-dir tmp/portal-preview`

This writes sanitized static HTML files for home, plans, dashboard, subscription detail, branded placeholder, help,
unavailable, degraded, expired, and not-found states. Generated previews are not committed.

## Safety Rules

- Dynamic values are HTML-escaped.
- Raw platform IDs are not shown; the dashboard uses `public_customer_code`.
- Raw portal tokens and raw session ids are never persisted or rendered; only hashes are stored.
- Raw subscription/proxy links, QR payloads, admin paths, node IPs, node hostnames, and private customer data are not rendered.
- The branded link appears only as the literal placeholder `https://sub.unseen.click/s/<opaque-token>`.
- Availability uses Phase 7 entitlement/resilience output but renders only customer-safe region/protocol status.
- No web server, nginx/TLS, systemd unit, live cookie service, or public route is configured in Phase 8B/8C.
- Phase 8C HTTP boundary is local-only: the adapter is exercised in-memory; the preview server binds loopback
  only and refuses public binds. Session cookies are HttpOnly+Secure+SameSite+Path; CSRF tokens are signed,
  constant-time-verified, and expiring; access logs are sanitized by construction. Future POST routes must
  require CSRF; GET-only render routes are exempt by design.

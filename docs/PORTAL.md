# PORTAL

> **Status:** Phase 8B foundation — render-only, dry-run, auth/session primitives only.

The customer portal foundation is a stdlib-only HTML renderer under `backend/portal_*`.
It is not a running service and has no real login yet.

## Timezone

Portal-visible subscription start/end, payment/order, invoice/receipt, and support dates use Myanmar Time (**MMT**,
UTC+06:30, `Asia/Yangon`). Current dry-run sample pages label subscription dates as MMT; future live rendering should
format app-created timestamps through `backend.timezone`.

## Boundary

- `backend/portal_app.py` exposes `render(conn, path, session_context=None)`.
- `backend/portal_routes.py` maps dry-run route shapes to `PortalResponse` objects.
- `backend/portal_viewmodels.py` reads DB-backed plans, subscriptions, delivery flags, and Phase 7 availability.
- `backend/portal_templates.py` escapes dynamic HTML and renders compact responsive pages.
- `backend/portal_static.py` embeds local CSS only; no CDN, fonts, images, or scripts.
- `backend/portal_auth.py` provides render-only `PortalSessionContext` helpers.
- `backend/portal_tokens.py`, `portal_access.py`, `portal_sessions.py`, and `branded_link_resolver.py` provide
  hash-only access/session primitives.

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
- No web server, nginx/TLS, systemd unit, live cookie service, or public route is configured in Phase 8B.

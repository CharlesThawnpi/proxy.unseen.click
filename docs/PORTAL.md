# PORTAL

> **Status:** Phase 8 foundation — render-only, dry-run, no public endpoint.

The customer portal foundation is a stdlib-only HTML renderer under `backend/portal_*`.
It is not a running service and has no real login yet.

## Boundary

- `backend/portal_app.py` exposes `render(conn, path, customer_id=None)`.
- `backend/portal_routes.py` maps dry-run route shapes to `PortalResponse` objects.
- `backend/portal_viewmodels.py` reads DB-backed plans, subscriptions, delivery flags, and Phase 7 availability.
- `backend/portal_templates.py` escapes dynamic HTML and renders compact responsive pages.
- `backend/portal_static.py` embeds local CSS only; no CDN, fonts, images, or scripts.
- `backend/portal_auth.py` is a future-auth placeholder and intentionally raises if used.

## Pages

- `/` landing/home placeholder.
- `/plans` DB-driven plan table.
- `/customer/status` customer dashboard using `public_customer_code`.
- `/subscriptions/<id>` subscription snapshot/status detail.
- `/s/<opaque-token>` branded-link landing/status placeholder only; no resolution.
- `/help`, `/unavailable`, `/expired`, `/not-found`.

## Dry-Run Tools

- `python3 bin/portal_smoke.py`
- `python3 bin/portal_render_dry_run.py --page subscription --out /tmp/unseen_portal_subscription.html`

Both default to a fresh temp DB, seed sample data, render HTML, and exit. They do not start a server,
read production DB by default, generate real tokens, fetch Hiddify output, or send Telegram messages.

## Safety Rules

- Dynamic values are HTML-escaped.
- Raw platform IDs are not shown; the dashboard uses `public_customer_code`.
- Raw subscription/proxy links, QR payloads, admin paths, node IPs, node hostnames, and private customer data are not rendered.
- The branded link appears only as the literal placeholder `https://sub.unseen.click/s/<opaque-token>`.
- Availability uses Phase 7 entitlement/resilience output but renders only customer-safe region/protocol status.
- No web server, nginx/TLS, systemd unit, or public route is configured in Phase 8.


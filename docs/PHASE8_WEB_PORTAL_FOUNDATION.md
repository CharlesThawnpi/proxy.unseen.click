# PHASE 8 — WEB / CUSTOMER PORTAL FOUNDATION

> **Date/time UTC:** 2026-06-16T06:29:58Z  
> **Result:** PASS — dry-run render-only foundation; no server, no public endpoint.

## Scope

Built the customer-facing portal foundation for local dry-run rendering only. The goal was a compact,
GitHub-inspired neutral webapp style, Burmese-primary copy with English product terms, DB-driven plan/status data,
Phase 7 availability rendering, and branded subscription-link groundwork without enabling live delivery or auth.

## Files Created / Changed

- Created `backend/portal_app.py`
- Created `backend/portal_routes.py`
- Created `backend/portal_templates.py`
- Created `backend/portal_viewmodels.py`
- Created `backend/portal_static.py`
- Created `backend/portal_auth.py`
- Created `bin/portal_render_dry_run.py`
- Created `bin/portal_smoke.py`
- Created `tests/test_portal.py`
- Created `docs/PORTAL.md`
- Updated `docs/CURRENT_STATUS.md`
- Updated `docs/CHANGELOG.md`
- Updated `docs/SECURITY.md`
- Updated `docs/DEPLOYMENT.md`
- Updated `docs/BOT_FLOWS.md`
- Regenerated `SOURCE_OF_TRUTH.md`

## Portal App / Router Behavior

`backend/portal_app.render(conn, path, customer_id=None)` is the app boundary. It returns a
`PortalResponse(status_code, body, content_type)` from route functions without opening sockets or starting a server.

Implemented route shapes:

- `/`
- `/plans`
- `/customer/status`
- `/subscriptions/<id>`
- `/s/<opaque-token>`
- `/help`
- `/unavailable`
- `/expired`
- `/not-found`

Unknown paths return the not-found page.

## UI Style / Design Decision

The CSS is GitHub-inspired only: compact, bordered panels, muted backgrounds, dense tables/lists, clear status badges,
small readable typography, and responsive mobile/desktop layout. No GitHub branding, logos, exact assets, external
fonts, images, or CDN dependencies are copied or referenced.

## Pages Implemented

- Landing/home placeholder.
- Customer dashboard/status page.
- Plans page.
- Subscription detail/status page.
- Branded subscription-link landing/status placeholder.
- Help/support page.
- Unavailable, expired, and not-found pages.

## Plan / Status / Availability Rendering

- Plans are read from DB rows (`plans`, `proxy_regions`, `protocol_profiles`, entitlement tables), not hardcoded.
- DE default, SG premium-only PRO/MAX, and the Fast display rule are preserved via existing entitlement helpers.
- Subscription pages show snapshot values from `subscriptions` (`snap_data_limit_gib`, `snap_duration_days`,
  `snap_price_mmk`) and safe lifecycle/provisioning statuses.
- Availability uses `availability.resolve(..., mode=dry_run)` from Phase 7 and renders customer-safe region/protocol
  status without node IPs, hostnames, or operational details.

## Branded Link Placeholder Behavior

Subscription detail pages display only:

`https://sub.unseen.click/s/<opaque-token>`

The `/s/<opaque-token>` route proves the route shape but does not resolve the token, fetch live data, show raw payloads,
or persist anything. Deep-link, copy-link, and QR states render as planned/available according to any safe delivery row;
QR remains planned unless a future implementation explicitly enables it.

## Security / Escaping Behavior

- All dynamic HTML values are escaped with `html.escape`.
- No inline untrusted HTML is accepted.
- Raw platform IDs are not displayed; dashboard identity is `public_customer_code`.
- Raw subscription/proxy links, token values, QR payloads, admin paths, node IPs, node hostnames, Hiddify secrets, and
  private customer data are not rendered.
- The CSS is local and embedded; no external script/font/image references.

## Dry-Run / No-Server Guarantees

- No web server started.
- No systemd unit created.
- No nginx/TLS/public endpoint configured.
- No real login/auth enabled.
- No Hiddify API call or live subscription fetch.
- No Telegram send/poll.
- No real customer/subscription/payment created; CLIs default to temp DB/sample data.

## Tests And Results

- `python3 -m unittest discover -s tests -p 'test_portal.py'` — 11 PASS.
- `python3 bin/portal_smoke.py` — PASS; all route shapes rendered, no server started.
- Full suite result after Phase 8: 174 PASS.

## Secret-Safety Result

Portal tests assert rendered HTML does not contain raw proxy schemes, Hiddify admin paths, the de1 public IP/hostname,
UUID-shaped strings, or sample opaque token values. The branded link is placeholder-only.

## Known Limits

- No public deployment.
- No real portal auth.
- No live `/s/<opaque-token>` resolution.
- No live Hiddify provisioning or subscription fetch.
- No QR generation.
- No admin portal.

## Live Blockers

- No public deployment yet.
- No real portal auth yet.
- No live subscription resolution.
- No live Hiddify provisioning.
- de1 rebuild still required before real provisioning.


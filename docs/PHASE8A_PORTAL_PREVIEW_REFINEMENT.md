# PHASE 8A — PORTAL PREVIEW REFINEMENT

> **Date/time UTC:** 2026-06-16T06:48:48Z  
> **Result:** PASS — local preview artifacts generated under git-ignored `tmp/`; no server, no public endpoint.

## Scope

Refined the Phase 8 customer portal for local visual review. This task improved the compact responsive UI,
Burmese-primary customer copy, status readability, and preview export workflow while preserving the render-only,
secret-safe, dry-run boundary.

## Files Created / Changed

- Created `bin/portal_preview_export.py`
- Changed `backend/portal_static.py`
- Changed `backend/portal_templates.py`
- Changed `backend/portal_viewmodels.py`
- Changed `backend/portal_routes.py`
- Changed `bin/portal_render_dry_run.py`
- Changed `bin/portal_smoke.py`
- Changed `tests/test_portal.py`
- Updated `docs/PHASE8_WEB_PORTAL_FOUNDATION.md`
- Updated `docs/PORTAL.md`
- Updated `docs/SECURITY.md`
- Updated `docs/DEPLOYMENT.md`
- Updated `docs/CURRENT_STATUS.md`
- Updated `docs/CHANGELOG.md`
- Regenerated `SOURCE_OF_TRUTH.md`

## UI Refinement Summary

- Reduced vertical padding and card/table spacing for a denser reviewable layout.
- Added a compact subscription quick-status strip.
- Improved mobile table behavior: rows stack as labeled cards below narrow widths, avoiding obvious horizontal overflow.
- Tightened status badges for subscription, region, protocol, unavailable, and degraded states.
- Kept touch targets usable and links keyboard-focusable.

## GitHub-Inspired Style Decision

The interface remains GitHub-inspired in broad product feel only: muted backgrounds, bordered panels, dense tables,
compact cards, and status badges. No GitHub branding, trademarks, logos, exact assets, external fonts, images, scripts,
or proprietary UI were copied.

## Preview Pages Generated

`bin/portal_preview_export.py` renders these sample pages:

- `home.html`
- `plans.html`
- `dashboard.html`
- `subscription.html`
- `branded-placeholder.html`
- `help.html`
- `unavailable.html`
- `degraded.html`
- `expired.html`
- `not-found.html`

Mobile-narrow review is covered by responsive CSS in the same HTML files, not separate mobile-only output.

## Preview Artifact Path

Generated local preview files:

`/opt/unseen-proxy/tmp/portal-preview/`

The directory is under git-ignored `tmp/` and was not staged or committed.

## Burmese-Primary Copy Updates

- Home copy now frames the portal as a customer status/support review surface.
- Dashboard copy emphasizes `public_customer_code` as the safe customer identity.
- Subscription detail copy is shorter and more customer-facing.
- Help copy clarifies Plan/support and connection issue handoff without exposing operational details.
- Product terms remain English where intended: Plan, Trial, Basic, Core, Plus, Pro, Max, Fast, Fast1, Fast2, Secure.

## Security / Escaping Result

- Dynamic HTML remains escaped through `html.escape`.
- Preview export scans rendered HTML for forbidden raw proxy/Hiddify URL shapes and UUID-shaped values.
- The single-page renderer and preview exporter refuse output paths outside `/opt/unseen-proxy/tmp/`.
- No preview artifact contains real tokens, raw opaque tokens, UUIDs, admin paths, proxy links, QR payloads, node
  hostnames, or private customer data.

## Dry-Run / No-Server Guarantees

- No web server started.
- No systemd unit created or enabled.
- No nginx/TLS/public endpoint configured.
- No real portal auth enabled.
- No Hiddify API call, live subscription fetch, Hiddify user creation, or node mutation.
- No Telegram send/poll/sender started.
- No real customer/subscription/payment created; CLIs use temp DB/sample data.

## Tests And Results

- `python3 -m unittest discover -s tests -p 'test_portal.py'` — 16 PASS.
- `python3 bin/portal_preview_export.py --out-dir tmp/portal-preview` — PASS.
- `python3 bin/portal_smoke.py` — PASS.
- `python3 bin/portal_render_dry_run.py --page subscription --out tmp/portal-preview-single/subscription.html` — PASS.
- Full suite result after Phase 8A: 179 PASS.

## Secret-Safety Result

Generated previews were scanned with `rg` for Hiddify/proxy schemes, admin path patterns, UUID-shaped strings, sample
opaque token values, platform sample ids, and node hostnames. No matches were found. Generated previews remain in
git-ignored `tmp/` only.

## Known Limits

- No public deployment.
- No real portal auth.
- No live `/s/<opaque-token>` resolution.
- No live Hiddify provisioning or subscription fetch.
- No QR generation.
- No admin portal.
- Preview files are static artifacts for human review only.

## Live Blockers

- No public deployment yet.
- No real portal auth yet.
- No live subscription resolution.
- No live Hiddify provisioning.
- de1 rebuild still required before real provisioning.

## Risks / Follow-Ups

- Future live portal deployment needs a real HTTP boundary, access logging policy, rate limits, and short-lived portal
  auth before exposing any route.
- `/s/<opaque-token>` still needs a separate sidecar/resolution design that fetches live subscription output in memory
  only and never stores raw links.
- Visual review may request further spacing/copy changes after Charles opens the generated HTML files.

## Exact Next Recommended Task

Charles should review `/opt/unseen-proxy/tmp/portal-preview/*.html` locally. After visual approval, the next engineering
task should be either a gated monitor scheduler or a portal auth/link-resolution design document; do not deploy the
portal publicly until auth, logging, `/s/` resolution, and de1 live blockers are handled.


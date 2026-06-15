# HIDDIFY API CONTRACT

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §14.1, Appendix C, §34 (Phase 3)
> **Status:** Phase 1 skeleton — structure only; every value verified in Phase 3

The verified Hiddify Manager **API v2** contract — endpoints, fields, units, and link/deep-link formats — pinned per Hiddify version per node.

> This document is a structured skeleton. **Nothing here is trustworthy until probed against a pinned Hiddify version on a real node.** The exact field names, units, and endpoint paths must be verified against the actual installed version before any code depends on them; the API changes between versions. The read-only `hiddify_api_probe.py` is a Phase 3 deliverable that generates this contract from the panel's Swagger/OpenAPI (Settings → API).

## API v2 base & auth

> Verified in Phase 3
> Base: `https://<node-domain>/<secret-proxy-path>/api/v2/admin/` — the `secret-proxy-path` lives in `.env`, never in the DB or logs. Auth header `Hiddify-API-Key: <key>` (key passed in header, not URL). Always v2.

## User: create

> Verified in Phase 3
> `POST …/admin/user/` — confirm exact path and field names. Fields seen in the API: `uuid, name, usage_limit_GB, package_days, current_usage_GB, start_date, mode, comment, telegram_id, enable`.

## User: update

> Verified in Phase 3
> `PATCH …/admin/user/<uuid>/` — change quota / expiry / enable.

## User: disable / suspend

> Verified in Phase 3
> `PATCH` with `enable=false` (preferred reversible action). Delete only on teardown.

## User: read / list

> Verified in Phase 3
> Get user `GET …/admin/user/<uuid>/`; list users `GET …/admin/user/`.

## Usage read

> Verified in Phase 3
> From the user record (`current_usage_GB`) or the user-facing `…/api/v2/user/me/` endpoint.

## Units (GB vs GiB — to confirm)

> Verified in Phase 3
> Confirm whether `usage_limit_GB` / `current_usage_GB` are GB or GiB (or bytes) against the installed version, and reconcile with the Master's `data_limit_gib`.

## Subscription URL format

> Verified in Phase 3
> Per-user link `https://<node-domain>/<secret-proxy-path>/<user-uuid>/` with format suffixes. A single user link returns all enabled protocols/domains on that panel. Never handed raw to customers — fetched by the Master sidecar and re-served as `https://sub.unseen.click/s/<token>`.

## Best output format for Hiddify App

> Verified in Phase 3
> Format suffixes: `/auto/`, `/sub/`, `/sub64/`, `/singbox/`, `/clash/`, `/clashmeta/` (and normal/xray). `auto` detects the client by User-Agent and returns the best format. Confirm the best output format for the Hiddify App in Phase 3.

## Deep-link scheme variants

> Verified in Phase 3
> Hiddify App URL scheme to confirm on a real device:
> - `hiddify://import/<sub-link>#<name>`
> - `hiddify://install-sub?url=<url-encoded sub-link>#<name>`
> - `hiddify://install-config?url=<url-encoded config>#<name>`
> - `hiddify://install-proxy?url=<url-encoded proxy share link>#<name>`
> The app also parses `clash://`, `clashmeta://`, `sing-box://`. Add-profile supports clipboard and in-app QR scan. Gallery-QR import is not reliable — lead with deep link + clipboard.

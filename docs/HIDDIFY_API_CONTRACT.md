# HIDDIFY API CONTRACT

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §14.1, Appendix C, §34 (Phase 3)
> **Status:** Phase 3 audit (docs) — base/auth **verified from official docs**; CRUD/fields/units **need live Swagger**.
> Tiers: **[VERIFIED]** official docs · **[LIVE]** confirm on a real install · **[ASSUMPTION]** do not depend yet.
> See [PHASE3_HIDDIFY_AUDIT_PLAN.md](PHASE3_HIDDIFY_AUDIT_PLAN.md).
> **Live install DONE on de1 (2026-06-16): Hiddify v12.3.3 running.** Partially verified, rest pending the browser Swagger:
> - **[VERIFIED-LIVE]** Installed **Hiddify Manager v12.3.3**; API title **"Hiddify API v2.2.0"**; auth header
>   **`Hiddify-API-Key: <admin-UUID>`** (the admin UUID is the credential); admin link form
>   `https://<node-domain>/<admin_proxy_path>/<admin_uuid>/`.
> - **[VERIFIED-LIVE]** Inbounds present: **Hysteria2 (FAST1), Shadowsocks (FAST2, :8388), VLESS-Reality (Secure)**.
> - **[LIVE — STILL PENDING]** exact user create/update/get/list/disable **paths**, field names + **units**, and
>   subscription output formats. The v12.3.3 API base path was **not black-box-discoverable** (probes hit Hiddify's
>   decoy site) and the **OpenAPI JSON route errors (HTTP 500/404)** — likely the apiflask/**marshmallow-v4** spec bug
>   (a `marshmallow<=3.26.1` pin is present-but-commented in Hiddify's installer). **Read these from the panel's browser
>   Swagger**, or fix the spec route, then fill below. See [PHASE3_DE1_HIDDIFY_LIVE_VERIFY.md](PHASE3_DE1_HIDDIFY_LIVE_VERIFY.md).
> Phase 4 stays blocked until these `[LIVE]` fields are verified.

The verified Hiddify Manager **API v2** contract — endpoints, fields, units, and link/deep-link formats — pinned per Hiddify version per node.

> This document is a structured skeleton. **Nothing here is trustworthy until probed against a pinned Hiddify version on a real node.** The exact field names, units, and endpoint paths must be verified against the actual installed version before any code depends on them; the API changes between versions. The read-only `hiddify_api_probe.py` is a Phase 3 deliverable that generates this contract from the panel's Swagger/OpenAPI (Settings → API).

## API v2 base & auth

> **[VERIFIED]** (official API docs)
> Three base path families:
> - Admin: `https://<node-domain>/<admin_proxy_path>/api/v2/admin/…`
> - Panel: `https://<node-domain>/<admin_proxy_path>/api/v2/panel/…` (e.g. `…/panel/version`)
> - User:  `https://<node-domain>/<user_proxy_path>/api/v2/user/…`
>
> Auth: header **`Hiddify-API-Key: <UUID>`** — the value is the **admin (or user) UUID** obtained from the admin/
> settings section, passed in the **header, not the URL**. **Treat this UUID as a secret** (it is the credential):
> store in `.env` by handle, never in the DB, logs, or git. The `<admin_proxy_path>`/`<user_proxy_path>` are
> **secret proxy paths** — also `.env`-only, never logged. **Always use v2** (v1 is deprecating).

## User: create

> **[LIVE]** confirm exact path/fields/units against the installed panel's Swagger before code depends on it
> `POST …/admin/user/` — confirm exact path and field names. Fields seen in the API: `uuid, name, usage_limit_GB, package_days, current_usage_GB, start_date, mode, comment, telegram_id, enable`.

## User: update

> **[LIVE]** confirm exact path/fields/units against the installed panel's Swagger before code depends on it
> `PATCH …/admin/user/<uuid>/` — change quota / expiry / enable.

## User: disable / suspend

> **[LIVE]** confirm exact path/fields/units against the installed panel's Swagger before code depends on it
> `PATCH` with `enable=false` (preferred reversible action). Delete only on teardown.

## User: read / list

> **[LIVE]** confirm exact path/fields/units against the installed panel's Swagger before code depends on it
> Get user `GET …/admin/user/<uuid>/`; list users `GET …/admin/user/`.

## Usage read

> **[LIVE]** confirm exact path/fields/units against the installed panel's Swagger before code depends on it
> From the user record (`current_usage_GB`) or the user-facing `…/api/v2/user/me/` endpoint.

## Units (GB vs GiB — to confirm)

> **[LIVE]** confirm exact path/fields/units against the installed panel's Swagger before code depends on it
> Confirm whether `usage_limit_GB` / `current_usage_GB` are GB or GiB (or bytes) against the installed version, and reconcile with the Master's `data_limit_gib`.

## Subscription URL format

> **[LIVE]** confirm exact path/fields/units against the installed panel's Swagger before code depends on it
> Per-user link `https://<node-domain>/<secret-proxy-path>/<user-uuid>/` with format suffixes. A single user link returns all enabled protocols/domains on that panel. Never handed raw to customers — fetched by the Master sidecar and re-served as `https://sub.unseen.click/s/<token>`.

## Best output format for Hiddify App

> **[LIVE]** confirm exact path/fields/units against the installed panel's Swagger before code depends on it
> Format suffixes: `/auto/`, `/sub/`, `/sub64/`, `/singbox/`, `/clash/`, `/clashmeta/` (and normal/xray). `auto` detects the client by User-Agent and returns the best format. Confirm the best output format for the Hiddify App in Phase 3.

## Ports, nginx & install behavior (Master/DE co-location)

> **Not verified yet — Phase 3 pending.**
> Hiddify Manager's actual public/panel/proxy port layout, its bundled web-server/TLS behavior, and whether its
> installer touches the host firewall (ufw/iptables) are **unknown and must not be assumed**. The Phase 2 preflight
> (`PHASE2_MASTER_DE_HIDDIFY_PREFLIGHT.md`) flagged the 80/443 + TLS ownership conflict (B1) and firewall exposure
> (B3) as install blockers. These are resolved by the Phase 3 read-only audit on a pinned version before any
> co-located install on the Master is authorized.

## Deep-link scheme variants

> **[LIVE]** confirm exact path/fields/units against the installed panel's Swagger before code depends on it
> Hiddify App URL scheme to confirm on a real device:
> - `hiddify://import/<sub-link>#<name>`
> - `hiddify://install-sub?url=<url-encoded sub-link>#<name>`
> - `hiddify://install-config?url=<url-encoded config>#<name>`
> - `hiddify://install-proxy?url=<url-encoded proxy share link>#<name>`
> The app also parses `clash://`, `clashmeta://`, `sing-box://`. Add-profile supports clipboard and in-app QR scan. Gallery-QR import is not reliable — lead with deep link + clipboard.

# HIDDIFY API CONTRACT

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §14.1, Appendix C, §34 (Phase 3)
> **Status:** Phase 3 audit (docs) — base/auth **verified from official docs**; CRUD/fields/units **need live Swagger**.
> Tiers: **[VERIFIED]** official docs · **[LIVE]** confirm on a real install · **[ASSUMPTION]** do not depend yet.
> See [PHASE3_HIDDIFY_AUDIT_PLAN.md](PHASE3_HIDDIFY_AUDIT_PLAN.md).
> ## 🔁 RE-VERIFIED-LIVE after fresh rebuild (Phase 9, 2026-06-16)
> After a fresh de1 rebuild + clean Hiddify v12.3.3 reinstall, the contract below was **re-confirmed live**: auth
> header `Hiddify-API-Key: <admin-UUID>`; admin API base **`https://<domain>/<proxy_path>/api/v2/admin/…`** (admin
> UUID in the **header**, NOT in the API path — the UUID appears only in the admin *UI* link
> `…/<proxy_path>/<admin_uuid>/`); `GET /admin/me/`→200, `GET /admin/user/`→200 (array); disposable-user
> create→get→all-configs(~14.8 KB)→patch→delete→re-GET 404; user fields + **GB units** unchanged. **Environment
> caveat:** apiflask 3.0.2 declares only `marshmallow>=3.20` (no upper bound), so a fresh install pulls **marshmallow
> 4.x**, which breaks API-v2 blueprint registration (every `/api/v2/*` → app-level 404). Fix = pin
> **`marshmallow==3.26.1`** in the Hiddify venv (the installer's own commented workaround) and restart `hiddify-panel`;
> re-apply after any Hiddify update that reinstalls marshmallow 4.x. See
> [PHASE9_DE1_REBUILD_FRESH_HIDDIFY.md](PHASE9_DE1_REBUILD_FRESH_HIDDIFY.md).
> ### 🌐 Domain/host: node-de.unseen.click verified-live (2026-06-16)
> The admin base + user subscription endpoints are now confirmed over the **real node domain with valid TLS** (not just
> the install's raw-IP/sslip.io defaults): `GET https://node-de.unseen.click/<proxy_path>/api/v2/admin/me/` → 200 and
> `/admin/user/` → 200 with `ssl_verify_result=0` (no `-k`); a disposable user's `/admin/all-configs/?uuid=…` (~16.4 KB)
> **references `node-de.unseen.click`**. The node domain + its Let's Encrypt cert are set via `hiddifypanel add-domain -m
> direct` + `apply_configs.sh` — see [HIDDIFY_NODE_INSTALL_RUNBOOK.md](HIDDIFY_NODE_INSTALL_RUNBOOK.md) §5A. The bare
> domain root `/` returns **502 by design** (Hiddify camouflage); always probe the `/<proxy_path>/api/v2/…` path.
> ### 📥 Subscription-output behavior (verified 2026-06-16) — for real-device import readiness
> - The **clean source of truth** for a user's configs is the admin endpoint `GET
>   /<proxy_path>/api/v2/admin/all-configs/?uuid=<uuid>` (200; ~16 KB; contains the hy2/ss/vless+reality outbounds).
> - The user-facing format URLs `…/<user_uuid>/{auto,sub,sub64,singbox,clash}/` **302-redirect to an HTML user-portal
>   page for an unmatched User-Agent** (`text/html`, no `outbounds`) — expected, not the raw config. The structured
>   `…/<user_uuid>/api/v2/user/all-configs/` returned **400** without the right params. Don't treat the HTML page as the
>   config when scanning.
> - Output is **multi-domain**: it lists every configured `direct` domain (node-de **and** the install's raw-IP +
>   sslip.io). Only the node-domain entries have a matching cert; raw-IP/sslip entries won't connect. There is **no
>   supported CLI** to remove a domain or set a primary sub domain (`hiddifypanel` exposes `add-domain` only) — prune via
>   the panel **Settings → Domains** if a single-domain output is wanted.
> - A client error like *"connection refused 127.0.0.1:<port>"* on **add profile** is the **Hiddify App's own local
>   core/clash-api port** (the sing-box template's clash-api is the standard `127.0.0.1:9090`; the node emits no such
>   remote target) — an **app-side** condition, not a node/API fault. Always run the §5B sanitized output inspection
>   before attributing an import failure to the node.
> - **Client-parser compatibility (verified 2026-06-16):** a `[SingboxParser] unmarshal error:
>   outbounds[N].tunnel-per-resolver: json: unknown field` means the generated sing-box config carries a field the app's
>   bundled core doesn't know, and the app rejects the **entire** profile. `tunnel-per-resolver` comes **only** from the
>   **DNSTT** outbound (`hutils/proxy/shared.py` + `singbox.py:add_dnstt`). Disable that transport with the supported CLI
>   `hiddifypanel set-setting -k dnstt_enable -v false` + `apply_configs.sh` (reversible). `get_proxies()` then omits the
>   DNSTT proxy (`shared.py:154-155`). The full sing-box config is rendered by `hutils.proxy.singbox.configs_as_json(**
>   get_common_data(uuid,'new'))` (the `/<proxy_path>/<uuid>/singbox/` endpoint) — but that route serves the HTML portal
>   to unrecognized UAs, so verify via an on-node app-context render (counts only).
> ### 🧹 Protocol/domain pruning levers (verified 2026-06-16) — for an UNSEEN-only profile
> The customer profile composition is governed by `hutils/proxy/shared.py:get_proxies()` (each `*_enable` hconfig strips
> matching Proxy rows) and `panel/user/user.py:362` (customer-sub domains = `Domain.sub_link_only != True`). Set protocol
> flags with `hiddifypanel set-setting -k <key> -v <bool>` (supported CLI). To deliver only **Hysteria2 (FAST1) +
> Shadowsocks (FAST2) + VLESS-Reality (Secure)**: enable `hysteria_enable`, `shadowsocks2022_enable`, `reality_enable`,
> `tcp_enable`; disable `vmess/tuic/naive/mieru/ssh_server/wireguard/trojan/dnstt/grpc/xhttp/httpupgrade/h2/ws/kcp/
> ssfaketls/shadowtls`; and set **`vless_enable=false`** (keeps **only** Reality vless). Exclude raw-IP/sslip from
> customer subs by setting `sub_link_only=1` on those Domain rows (no `remove-domain` CLI exists). Full recipe:
> [HIDDIFY_NODE_INSTALL_RUNBOOK.md](HIDDIFY_NODE_INSTALL_RUNBOOK.md) §5C.

> ## ✅ VERIFIED-LIVE on de1 — Hiddify **v12.3.3**, API **"Hiddify API v2.2.0"** (2026-06-16)
> Source: the panel's own OpenAPI spec (generated in-process via `hiddifypanel`/apiflask — 22 paths) **and** confirmed
> by live HTTP calls (create/get/delete a disposable user, 200s). The earlier OpenAPI HTTP failures were **routing/
> decoy** (wrong proxy_path), **not** a marshmallow bug — the spec builds fine, so **no package change was made**.
>
> - **Auth:** header **`Hiddify-API-Key: <admin-UUID>`** (`apiKey`, `in: header`). The admin UUID is the credential — secret.
> - **Base path families** (`<proxy_path>` = secret; admin UUID via header, NOT in admin-API path):
>   - Admin: `https://<node-domain>/<proxy_path>/api/v2/admin/…`
>   - User:  `https://<node-domain>/<proxy_path>/api/v2/user/…` and `…/<proxy_path>/<user_secret_uuid>/api/v2/user/…`
> - **User CRUD (admin):** `GET /admin/user/` (list) · `POST /admin/user/` (create) · `GET|PATCH|DELETE /admin/user/{uuid}/`.
>   Also: `/admin/user/{uuid}/`, `/admin/me/`, `/admin/server_status/`, `/admin/all-configs/`, `/admin/update_user_usage/`.
> - **User schema fields** (`UserSchema`/`PostUserSchema`/`PatchUserSchema`): `uuid`, `name`, **`usage_limit_GB`** (number),
>   **`package_days`** (int), **`current_usage_GB`** (number), `start_date` (date), `mode` (reset mode), `comment`,
>   `telegram_id`, `enable` (bool), `is_active` (bool), `lang`, `last_online`, `last_reset_time`, `added_by_uuid`,
>   `ed25519_*`/`wg_*` keys (server-generated), `id` (read-only).
> - **⚠ UNITS = GB (not GiB):** `usage_limit_GB` / `current_usage_GB` are **gigabytes** (per the schema descriptions).
>   The plan stores `data_limit_gib` → **the orchestrator MUST convert GiB↔GB** when talking to Hiddify.
> - **Subscription/config output:** `GET …/api/v2/user/all-configs/` and `…/user/me/` (also uuid-in-path variants);
>   admin can fetch via `/admin/all-configs/?uuid=<uuid>` (returned 200, ~14.8 KB for the test user). Output-format
>   suffixes (auto/sub/sub64/singbox/clash) are the user-link formats — confirm exact form when the sidecar is built.
> - **Disposable test user lifecycle VERIFIED:** create→200, GET→200, all-configs→200, DELETE→200, re-GET→404.
>
> **Phase 4 is UNBLOCKED for the API layer.** (Remaining node-tuning, not contract: SS :8388 + UDP proxy ports were
> not externally reachable in the firewall check — see [PHASE3_DE1_HIDDIFY_LIVE_VERIFY.md](PHASE3_DE1_HIDDIFY_LIVE_VERIFY.md).)

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

> **[VERIFIED-LIVE 2026-06-16, de1 v12.3.3]** — see the ✅ VERIFIED-LIVE summary at the top of this file for the
> confirmed paths/fields/units (GB), auth header, and subscription endpoints. Details below are consistent with it.
> `POST …/admin/user/` — confirm exact path and field names. Fields seen in the API: `uuid, name, usage_limit_GB, package_days, current_usage_GB, start_date, mode, comment, telegram_id, enable`.

## User: update

> **[VERIFIED-LIVE 2026-06-16, de1 v12.3.3]** — see the ✅ VERIFIED-LIVE summary at the top of this file for the
> confirmed paths/fields/units (GB), auth header, and subscription endpoints. Details below are consistent with it.
> `PATCH …/admin/user/<uuid>/` — change quota / expiry / enable.

## User: disable / suspend

> **[VERIFIED-LIVE 2026-06-16, de1 v12.3.3]** — see the ✅ VERIFIED-LIVE summary at the top of this file for the
> confirmed paths/fields/units (GB), auth header, and subscription endpoints. Details below are consistent with it.
> `PATCH` with `enable=false` (preferred reversible action). Delete only on teardown.

## User: read / list

> **[VERIFIED-LIVE 2026-06-16, de1 v12.3.3]** — see the ✅ VERIFIED-LIVE summary at the top of this file for the
> confirmed paths/fields/units (GB), auth header, and subscription endpoints. Details below are consistent with it.
> Get user `GET …/admin/user/<uuid>/`; list users `GET …/admin/user/`.

## Usage read

> **[VERIFIED-LIVE 2026-06-16, de1 v12.3.3]** — see the ✅ VERIFIED-LIVE summary at the top of this file for the
> confirmed paths/fields/units (GB), auth header, and subscription endpoints. Details below are consistent with it.
> From the user record (`current_usage_GB`) or the user-facing `…/api/v2/user/me/` endpoint.

## Units (GB vs GiB — to confirm)

> **[VERIFIED-LIVE 2026-06-16, de1 v12.3.3]** — see the ✅ VERIFIED-LIVE summary at the top of this file for the
> confirmed paths/fields/units (GB), auth header, and subscription endpoints. Details below are consistent with it.
> Confirm whether `usage_limit_GB` / `current_usage_GB` are GB or GiB (or bytes) against the installed version, and reconcile with the Master's `data_limit_gib`.

## Subscription URL format

> **[VERIFIED-LIVE 2026-06-16, de1 v12.3.3]** — see the ✅ VERIFIED-LIVE summary at the top of this file for the
> confirmed paths/fields/units (GB), auth header, and subscription endpoints. Details below are consistent with it.
> Per-user link `https://<node-domain>/<secret-proxy-path>/<user-uuid>/` with format suffixes. A single user link returns all enabled protocols/domains on that panel. Never handed raw to customers — fetched by the Master sidecar and re-served as `https://sub.unseen.click/s/<token>`.

## Best output format for Hiddify App

> **[VERIFIED-LIVE 2026-06-16, de1 v12.3.3]** — see the ✅ VERIFIED-LIVE summary at the top of this file for the
> confirmed paths/fields/units (GB), auth header, and subscription endpoints. Details below are consistent with it.
> Format suffixes: `/auto/`, `/sub/`, `/sub64/`, `/singbox/`, `/clash/`, `/clashmeta/` (and normal/xray). `auto` detects the client by User-Agent and returns the best format. Confirm the best output format for the Hiddify App in Phase 3.

## Ports, nginx & install behavior (Master/DE co-location)

> **Not verified yet — Phase 3 pending.**
> Hiddify Manager's actual public/panel/proxy port layout, its bundled web-server/TLS behavior, and whether its
> installer touches the host firewall (ufw/iptables) are **unknown and must not be assumed**. The Phase 2 preflight
> (`PHASE2_MASTER_DE_HIDDIFY_PREFLIGHT.md`) flagged the 80/443 + TLS ownership conflict (B1) and firewall exposure
> (B3) as install blockers. These are resolved by the Phase 3 read-only audit on a pinned version before any
> co-located install on the Master is authorized.

## Deep-link scheme variants

> **[VERIFIED-LIVE 2026-06-16, de1 v12.3.3]** — see the ✅ VERIFIED-LIVE summary at the top of this file for the
> confirmed paths/fields/units (GB), auth header, and subscription endpoints. Details below are consistent with it.
> Hiddify App URL scheme to confirm on a real device:
> - `hiddify://import/<sub-link>#<name>`
> - `hiddify://install-sub?url=<url-encoded sub-link>#<name>`
> - `hiddify://install-config?url=<url-encoded config>#<name>`
> - `hiddify://install-proxy?url=<url-encoded proxy share link>#<name>`
> The app also parses `clash://`, `clashmeta://`, `sing-box://`. Add-profile supports clipboard and in-app QR scan. Gallery-QR import is not reliable — lead with deep link + clipboard.

# PHASE 3-DE — Hiddify host install + live verify on de1

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §14, §34; [DECISIONS.md](DECISIONS.md) ADR-001/002; [PHASE2_DE1_PREFLIGHT.md](PHASE2_DE1_PREFLIGHT.md)
> **Result:** **PASS (with non-blocking follow-ups).** Hiddify Manager **v12.3.3** installed & running on de1; **API v2
> contract VERIFIED-LIVE**; **disposable test user create→verify→subscription→delete confirmed**; panel/API reachable
> externally on 443. Follow-up (non-blocking, node-tuning): SS `:8388` + UDP proxy ports not externally reachable
> (ufw/Hiddify-iptables), and a real-device protocol connect test. **Phase 4 is UNBLOCKED for the API layer.** Node
> stays `status=test`.
>
> ## Follow-up update (2026-06-16T02:37Z) — API contract recovered & verified
> - The earlier OpenAPI failures were **routing/decoy** (I'd parsed the wrong proxy_path), **not** the marshmallow-v4
>   bug: the spec **builds fine in-process** (22 paths). **No package change made** (the task's pin condition wasn't met).
> - Using the authoritative proxy_path (from `hiddifypanel admin-path`), live HTTP calls succeeded: **API contract fully
>   verified** (see [HIDDIFY_API_CONTRACT.md](HIDDIFY_API_CONTRACT.md)) and a **disposable-test user** was created
>   (`usage_limit_GB=1, package_days=1`), read back, its subscription `all-configs` returned (200, ~14.8 KB), then
>   **deleted (re-GET → 404)**. Users back to 1 (default).
> - **Reachability (from Master):** tcp **22/80/443 OPEN** (443 TLS → 200); **8388 (Shadowsocks) filtered**; UDP
>   (Hysteria2) not TCP-probeable → real-device test. ufw active (only 22 explicit; Hiddify added 4 proxy ACCEPT rules).
> - **⚠ Secret-safety incident (disclosed):** during API debugging, a shell-quoting bug (unquoted User-Agent with
>   spaces) mis-aligned curl args so a response body printed to the terminal, **exposing the Hiddify "default" user's
>   ed25519 private key + WireGuard keys + uuid**. It was **NOT committed to git** (terminal only), on a **no-customer
>   `test` node**. Remediation: these are the default-user/server keys on a throwaway test node; **regenerate the node's
>   default user / server secrets before any live use** (or they're moot once the node is rebuilt for production).
>   Process fix applied for the rest of the task: all API bodies written to files, never stdout; UA always quoted.

## Run metadata

| Field | Value |
|---|---|
| Date/time (UTC) | 2026-06-16T02:15Z |
| Node | `de1` — Germany / DE — `5.249.160.59` — `node-de.unseen.click` — status `planned/test` |
| OS | Ubuntu 22.04.5 LTS (kernel 5.15) |
| SSH | root key (`/root/.ssh/unseenproxy_de1_ed25519`); host key re-pinned after the reinstall |
| Install method | **official host installer, version-pinned**: `download.sh v12.3.3 --no-gui` (non-interactive; NOT Docker) |
| Hiddify version | **12.3.3** (panel API title reports **v2.2.0**) |
| Admin link | stored **only** at `/root/hiddify-de1-admin.link` (`0600`, root) — **value never printed/committed** |

## RAM (accepted risk) — balloon-dynamic, observed up to 3.8 GiB under load

Provider "disable ballooning" had not taken effect at gate time (node not power-cycled): idle RAM read **~1.8 GiB**.
Charles **accepted the RAM risk** (`ACCEPTED_RISK_RAM_LOW_FOR_TEST`) and we proceeded. **Observed during/after install
the balloon deflated to ~3.2–3.8 GiB available under memory pressure**, and **no OOM occurred**. Net: workable for a
test node; for production load, lock the full 4 GB via a VM stop→start or upgrade. Swap 2.1 GiB present.

## Pre-install gate (non-RAM) — PASS

OS 22.04.5 ✓ · disk 23 GB/17 GB free ✓ · static netplan + egress `5.249.160.59` ✓ · **DNS `node-de.unseen.click` →
`5.249.160.59` resolves (Master+node)** ✓ · SSH:22 + ufw active(22 allowed) ✓ · 80/443 free pre-install ✓ · no
nginx/docker/hiddify/legacy ✓ · clean scan ✓.

## Install + the permission cascade (transparent post-mortem)

The first install returned exit 0 but **no service started**. Root cause: **the agent set `umask 077` in the shell that
launched the installer**, which propagated into the install and created installer-made dirs as `700` (and poisoned the
**uv package cache** with `600` files). Because uv **hardlinks** cached files into the venv, a clean reinstall still
inherited them. Cascade + fixes (all my-umask remediation, with safe standard perms; libraries/interpreters are not secrets):

1. `/opt/hiddify-manager` was `700` → `CHDIR Permission denied`. **Fixed** by `rm -rf` + reinstall under **`umask 022`** (now `755`).
2. uv-managed Python `/usr/local/share/uv/...` was `700` → `203/EXEC Permission denied`. **Fixed** `chmod -R a+rX /usr/local/share/uv`.
3. venv libs `.venv313/lib/.../site-packages/*` were `600` (cache-poisoned) → `PermissionError: bjoern.py`. **Fixed** `chmod -R a+rX /opt/hiddify-manager/.venv313`.

After (1)–(3): `systemctl restart hiddify-panel` → **active**; `apply_configs.sh --no-gui --no-log` (rc 0) regenerated
configs → **all services active.** (Lesson recorded: never set a restrictive umask when launching third-party installers.)

## Services / ports / firewall after install

- **Services (all `active`):** hiddify-panel, hiddify-nginx, hiddify-haproxy, hiddify-xray, hiddify-singbox, mariadb (redis on loopback).
- **Listening:** `443/tcp` + `443/udp` (panel/sub + Hysteria2/QUIC), `8388` Shadowsocks, plus many Reality/other proxy
  inbound ports (TCP+UDP); `3306`/`6379` loopback only; **SSH `22` up**. 80/443 now owned by Hiddify's nginx/haproxy.
- **UFW:** `active`, explicitly allows only **22/tcp** (v4+v6). Hiddify manages its own iptables for the proxy ports.
  ⚠ **To verify:** that the proxy inbound ports are actually reachable externally given ufw's default-deny (Hiddify
  inserts its own ACCEPT rules; confirm coexistence). SSH stayed reachable throughout.
- **SSH safety:** confirmed listening + reachable at every step.
- **Resources after:** RAM ~3.8 GiB (2.8 avail) + 2.1 swap; disk 15 GB free; `/opt/hiddify-manager` `755`.

## Protocol / inbound verification — PASS (from generated configs; names only, no keys)

- **FAST1 = Hysteria2** — present (singbox inbound `hysteria2`; `443/udp` listening). ✓
- **FAST2 = Shadowsocks** — present (`shadowsocks` inbound; `8388` listening). ✓
- **Secure = VLESS-Reality** — present (xray `vless` inbound + `reality` config). ✓
- (Panel also exposes many other protocols — tuic, trojan, vmess, etc. — not in scope.)

## API / Swagger verification — DEFERRED (the one gap)

- Confirmed: API title **Hiddify API v2.2.0**; auth is header **`Hiddify-API-Key: <admin-UUID>`** (the admin UUID,
  from the admin-link structure + Hiddify docs); admin link form is `https://<node-domain>/<proxy_path>/<admin_uuid>/`.
- **Not obtained automatically:** the exact user CRUD endpoint paths, field names, units, and subscription output formats.
  - The panel **OpenAPI/Swagger JSON endpoint errors** (HTTP 500 on `/…/api/v2/openapi.json` at one path; 404 at others)
    — likely the **apiflask/marshmallow-v4** spec bug that Hiddify's own installer references (a `marshmallow<=3.26.1`
    pin is present-but-commented in `hiddify_installer.sh`).
  - Direct API probes (`/<proxy>/api/v2/admin/user/`, `/<proxy>/<uuid>/api/v2/admin/user/`, etc.) returned **404 + Hiddify's
    decoy camouflage site** — i.e. the v12.3.3 API base path differs from the documented/older structure and is not
    safely discoverable black-box. The CLI (`hiddifypanel routes`/`spec`) only registers static routes in CLI context.
- **No disposable test user was created** (it depends on the verified endpoint path; the CLI has no user-CRUD command).
  Nothing was guessed/forced.

## Disposable test user — NOT DONE (deferred with the API contract)

Will be created (`disposable-test`, no real data/payment/UNSEEN token) and deleted once the API path is known.

## Rollback path

- de1 is a fresh test node, no customer data → **provider reinstall** is the clean rollback (proven path). Hiddify also
  has `uninstall.sh`. The Master holds no dependency on de1 yet (Phase 4 not started).

## Remaining risks / blockers

- **API v2 contract not captured (blocks Phase 4 orchestrator).** Resolve via the browser Swagger (#TASK_for_Charles)
  or by fixing the OpenAPI 500 (try the Hiddify-referenced `marshmallow<=3.26.1` pin in the venv, then re-fetch).
- **ufw vs Hiddify iptables:** confirm proxy ports are externally reachable (ufw default-deny + Hiddify's own rules).
- **RAM** balloon-dynamic (accepted risk) — lock 4 GB before production.
- **Hardening deferred:** password SSH login still enabled on de1; disable after key access is confirmed (it is).
- The `marshmallow` spec bug suggests the **API serialization itself** may need that pin to work reliably — verify when capturing the contract.

## #TASK_for_Charles

1. Open the **admin link** (in `/root/hiddify-de1-admin.link`) in a browser → Hiddify admin panel → **API documentation /
   Swagger** section. That authoritatively shows the API v2 base path + user CRUD endpoints + fields. Share the structure
   (no secrets) so the contract can be recorded — or authorize a follow-up to apply `marshmallow<=3.26.1` and fetch the spec programmatically.
2. Optionally do a real-device **Hiddify App import** test from the panel to confirm FAST1/FAST2/Secure connect (links never logged here).

> **NOTE:** the "DEFERRED / NOT DONE" sections above are **superseded** by the 2026-06-16T02:37Z follow-up at the top —
> the API contract was recovered and verified, and the disposable test user lifecycle was completed. Kept for history.

## PASS / PARTIAL / FAIL — FINAL

**PASS (with non-blocking follow-ups).** Hiddify v12.3.3 running on de1; **API v2 contract VERIFIED-LIVE**; **disposable
test user create→verify→subscription→delete confirmed**; FAST1/FAST2/Secure inbounds present; panel/API reachable on
443; SSH safe; admin link secured. **Phase 4 is UNBLOCKED for the API layer.** Non-blocking follow-ups: SS `:8388`/UDP
proxy-port external reachability (ufw), a real-device connect test, lock 4 GB RAM, harden SSH, regenerate the leaked
default-user keys before live use.

## Exact next recommended task

1. **Begin Phase 4** (DB/backend + Hiddify orchestrator) against the verified contract in
   [HIDDIFY_API_CONTRACT.md](HIDDIFY_API_CONTRACT.md) — **remember GiB↔GB conversion** (Hiddify uses GB).
2. **Node-tuning follow-ups (before live):** open the proxy ports through ufw / verify Hiddify-iptables (SS:8388, UDP),
   real-device Hiddify-App connect test (#TASK_for_Charles), lock 4 GB RAM, disable SSH password login, and regenerate
   the default-user/server secrets (the leaked test-node keys). Node remains `status=test` until these are done.

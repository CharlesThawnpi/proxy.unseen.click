# PHASE 3-DE — Hiddify host install + live verify on de1

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §14, §34; [DECISIONS.md](DECISIONS.md) ADR-001/002; [PHASE2_DE1_PREFLIGHT.md](PHASE2_DE1_PREFLIGHT.md)
> **Result:** **PARTIAL.** Hiddify Manager **v12.3.3** is **installed and running** on de1 (all services active; FAST1/FAST2/Secure inbounds present; admin panel reachable on 443). **Deferred:** exact live API v2 CRUD contract + the disposable test user — the v12.3.3 API URL path isn't black-box-discoverable (path guesses hit Hiddify's decoy site) and the OpenAPI route errors. Best read from the **browser Swagger** (#TASK_for_Charles). **Node stays `status=test`.**

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

## PASS / PARTIAL / FAIL

**PARTIAL.** Install + service + protocol-inbound verification = **PASS** (Hiddify v12.3.3 fully running on de1, 443 up,
FAST1/FAST2/Secure present, admin link secured, SSH safe). **API v2 CRUD contract + disposable test user = deferred**
(v12.3.3 API path not discoverable black-box + OpenAPI route errors). **Phase 4 remains blocked** until the API contract is verified.

## Exact next recommended task

Capture the **verified API v2 contract** from the browser Swagger (or fix the OpenAPI 500 via `marshmallow<=3.26.1`),
fill [HIDDIFY_API_CONTRACT.md](HIDDIFY_API_CONTRACT.md), then create+delete one disposable test user and (optionally)
a real-device connect test. After that, **Phase 4** (DB/backend orchestrator) can begin against the verified contract.
Also: verify ufw/Hiddify proxy-port reachability, and lock 4 GB RAM before any live use.

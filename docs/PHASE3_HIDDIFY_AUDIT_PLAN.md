# PHASE 3 — Hiddify Install / API / Port / TLS Audit Plan

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §14, Appendix C, §34 Phase 3; builds on `PHASE2_MASTER_DE_HIDDIFY_PREFLIGHT.md`
> **Status:** Audit PLAN — **read-only research; no install, no system change, no Hiddify API call.**
> **Install-readiness decision:** **PARTIAL / HOLD** (plan ready; install still gated on live verification + B2 snapshot + a co-location-vs-separate-VPS decision by Charles).

This is the source-backed plan for *how* to later install Hiddify Manager on the protected Master/DE VPS without
breaking the control plane. Every claim is tiered: **[VERIFIED]** from current official/primary docs,
**[LIVE]** must be verified on a real install before code depends on it, **[ASSUMPTION]** do not depend on yet.

## Run metadata

| Field | Value |
|---|---|
| Date/time (UTC) | 2026-06-15T11:15:10Z |
| Host | Master `crimson-gorilla-49484` — Ubuntu 24.04.4, 4 vCPU / 16 GB / 100 GB |
| Task | Phase 3 audit **planning only** — Hiddify NOT installed |

## Sources consulted

- Hiddify docs — Installation prerequisites: https://hiddify.com/manager/installation-and-setup/Installation-prerequisites/
- Hiddify docs — How to use the API in HiddifyManager: https://hiddify.com/manager/contribution/How-to-use-API-in-HiddifyManager-project/
- Hiddify docs — How to setup Firewall: https://hiddify.com/manager/basic-concepts-and-troubleshooting/How-to-setup-Firewall-on-Hiddify-panel/
- Hiddify docs — Install using Docker: https://hiddify.com/manager/installation-and-setup/Install-Hiddify-using-Docker/
- DeepWiki — Installation Guide: https://deepwiki.com/hiddify/Hiddify-Manager/2-installation-guide
- DeepWiki — Docker Deployment: https://deepwiki.com/hiddify/Hiddify-Manager/2.2-docker-deployment
- GitHub — `common/utils.sh` (install path/venv): https://raw.githubusercontent.com/hiddify/Hiddify-Manager/main/common/utils.sh
- GitHub discussion #4740 — deploy behind a reverse proxy: https://github.com/orgs/hiddify/discussions/4740
- GitHub issue #4111 / PR #5159 — Ubuntu 24.04 / Redis 7.0 install fixes

> Public docs intentionally omit exact API field names/units and tell developers to read the panel's own
> Swagger/OpenAPI (Settings → API). That is the single biggest **[LIVE]** dependency in this audit.

---

## What the installer does (verified)

- **[VERIFIED] Install method:** a host `install.sh` (Python-orchestrated) **or** a Docker deployment. The standard
  install puts files under **`/opt/hiddify-manager/`** (Python venv `…/.venv313`) — **separate from `/opt/unseen-proxy/`**, so no project-path collision.
- **[VERIFIED] Host services the standard installer brings up:** **Nginx** (web entry + TLS termination),
  **HAProxy** (SNI proxy / traffic splitting), **Xray** (VLESS-Reality/XTLS), **Sing-box** (Hysteria2/TUIC),
  **MariaDB**, **Redis**, Python 3.13 venv. → On a standard install Hiddify **owns 80/443** via its own nginx+HAProxy.
- **[VERIFIED] Firewall:** the panel **manages iptables itself**, auto-creates rules for its service ports, auto-detects
  the SSH port, and warns *"Do not turn off the firewall."* When its firewall is on, service ports (incl. 22/80/443)
  stay open and non-service ports are closed.
- **[VERIFIED] OS:** official requirement is **Ubuntu 22.04**. Ubuntu 24.04 ships Redis 7.0 which caused install-order
  failures (issue #4111); fixes landed (PR #5159) but **24.04 is not officially blessed** → **[LIVE]** must pin a
  version proven on 24.04 (or use Docker, which bundles Redis and sidesteps the host-Redis issue).
- **[VERIFIED] Docker option:** default `docker-compose.yml` binds `80:80` and `443:443`, **but these can be remapped**
  (e.g. `8080`/`8443`) to run **behind an existing nginx** (discussion #4740). Docker bundles Redis/MariaDB in
  containers (less host mutation). **[VERIFIED]** Docker support is labelled **experimental**.

## Answers to the 9 audit questions

1. **Does Hiddify require 80/443, or can it coexist?** **[VERIFIED]** Standard install **takes 80/443** (own nginx+HAProxy).
   **[VERIFIED]** A **Docker install with remapped ports can coexist behind an existing nginx** for the **HTTP(S) panel/subscription**. **[LIVE]** Caveat: the **proxy inbounds are not plain HTTPS** — Hysteria2 is QUIC/**UDP**, VLESS-Reality is raw-TLS/SNI on (typically) **443/TCP**, Shadowsocks is its own TCP/UDP — these **cannot be HTTP-reverse-proxied by nginx** and need dedicated ports or SNI (HAProxy) fronting.
2. **What exactly does it change (nginx/certbot/firewall/Docker/systemd)?** **[VERIFIED]** standard install creates host
   systemd services (hiddify-nginx, hiddify-haproxy, xray, sing-box, mariadb, redis), manages **iptables**, and runs its
   **own ACME/TLS** (not the system certbot). **[LIVE]** exact unit names, cert mechanism, and whether it rewrites
   `/etc/iptables` vs an isolated chain must be observed on a snapshot/sandbox.
3. **Common ports exposed:** **[VERIFIED]** panel + subscription over **443** (HTTP/TLS) on a secret proxy path;
   **[LIVE/ASSUMPTION]** Reality ≈ 443/TCP (stealth), Hysteria2 ≈ a high UDP port, Shadowsocks ≈ its own port, admin/API
   share the panel 443 path. **Exact/default port numbers are panel-assigned and configurable → verify live; do not hardcode.**
4. **Can Master control-plane subdomains and `node-de` coexist on one VPS?** **[VERIFIED, conditional]** Yes for HTTP(S)
   **only via one front terminator on 443 doing host/SNI routing** — either Master-nginx-fronts (Option A) or
   Hiddify-HAProxy-fronts (Option B). **[LIVE]** Two independent processes cannot both bind 443; the proxy inbounds still
   need their own ports. A single shared public IP makes this an SNI-routing problem, not a "just add a vhost" problem.
5. **Safest TLS/domain strategy:** see "Recommended co-location architecture" — control-plane subdomains
   (`unseen.click`,`www`,`app`,`api`,`bot`,`panel`,`sub`) terminate on the Master's existing nginx design; the DE node
   uses its own `node-de.unseen.click` for Hiddify's panel/subscription/Reality SNI. **[LIVE]** final ownership of 443.
6. **Firewall allowlist before install (protecting SSH):** keep **22/tcp (SSH) explicitly allowed**, plus the planned
   control-plane 80/443; **do not enable a competing ufw/nft ruleset that Hiddify's iptables management would fight**.
   **[VERIFIED]** Hiddify auto-detects the SSH port — but verify SSH survives on a snapshot first, and ensure a
   provider **console/recovery** path exists in case of lockout.
7. **Realistic rollback if the installer changes host services:** **[VERIFIED-by-design]** standard host install =
   **provider snapshot is the only trustworthy rollback** (host-wide). **Docker install = materially easier rollback**
   (`docker compose down -v` + remove `/opt/hiddify-manager` Docker state). Either way B2 snapshot stays mandatory.
8. **What must be verified live before Phase 3 API coding begins:** the **[LIVE]** checklist below.
9. **API v2 — verified vs live:** **[VERIFIED]** base path shape, header auth = UUID, v2-only (see API_CONTRACT). **[LIVE]**
   exact user CRUD paths, field names, units (GB vs GiB), and subscription-format behavior — read from the panel's Swagger.

---

## B1 / B3 / B4 findings & resolutions

### B1 (HIGH) — 80/443 + TLS coexistence → **resolvable; decision required**

Three options, in increasing isolation/safety:

- **Option A (recommended for co-location): Docker Hiddify on remapped ports, Master nginx is the 443 front.**
  Master nginx owns 80/443 for all control-plane subdomains **and** reverse-proxies `node-de`/`panel`/`sub-de`
  **HTTP(S)** to Hiddify's container (e.g. `127.0.0.1:8443`). **Proxy inbounds get their OWN dedicated public ports**
  (Hysteria2 UDP port; SS port). **Reality cannot share 443 with nginx** → either give Reality a dedicated TCP port
  (slightly less stealthy) **[LIVE decision]** or front 443 with HAProxy (Option B). Bundled Redis sidesteps the 24.04 issue.
- **Option B: Hiddify HAProxy owns 443 with SNI routing; Master nginx sits behind it.** Most native to Hiddify and
  preserves Reality-on-443 stealth, but **inverts the Master's "nginx is sole owner of 443" design** and couples
  control-plane TLS availability to Hiddify's HAProxy — higher control-plane risk.
- **Option C (lowest risk overall): do NOT co-locate — put the DE node on its own small VPS.** §6.1 makes this a
  no-code-change move. Eliminates B1/B3/B4 on the Master entirely, at the cost of one more small VPS. **Recommended if
  control-plane safety outweighs the cost saving.**

➡ **Decision needed from Charles:** Option A (co-locate via Docker, recommended) vs Option C (separate DE VPS, safest).
Option B is documented but not recommended for a control plane.

### B3 — firewall exposure plan → **planned**

- Before install: confirm **SSH key access works**, a **provider console/recovery** path exists, and **no competing
  ufw/nft ruleset** is enabled (today: none — ufw inactive, iptables all-ACCEPT).
- Let Hiddify manage its own iptables (it auto-opens its service ports and the SSH port). **[LIVE]** immediately after
  install, verify from a *second* SSH session that 22 is still reachable before closing the first.
- Only the intended ports should be world-exposed: 80/443 (control plane), the DE proxy inbound ports, SSH. Everything
  else closed. Document the final allowlist post-install.

### B4 — installer behavior uncertainty → **reduced, not eliminated**

- Now **[VERIFIED]**: install path `/opt/hiddify-manager`, the host services it brings, iptables management, own ACME,
  Docker-with-remapped-ports coexistence, and the 24.04/Redis caveat.
- Still **[LIVE]**: exact systemd unit names, cert files, default protocol ports, and whether its iptables management
  touches custom chains — observe on a **snapshot/sandbox** first.

### B2 — provider snapshot → **STILL PENDING / MANUAL (Charles)**

Unchanged: a Master provider snapshot must be taken and confirmed by Charles **before** any install. Required for both
Option A and B; not needed for Option C (separate VPS) beyond that VPS's own baseline.

---

## Recommended co-location architecture (proposed, pending live verification)

```
                    Public IP (Master / DE)
                           │
            ┌──────────────┴───────────────┐
            │  443/TCP front terminator     │   (Option A: Master nginx; Option B: Hiddify HAProxy)
            │  routes by host/SNI:          │
            │   unseen.click/www/app/api/   │→ Master loopback services (8190/8191/8192/8197)
            │   bot/panel/sub               │
            │   node-de.unseen.click        │→ Hiddify panel+subscription (container 127.0.0.1:8443)
            └───────────────────────────────┘
   Dedicated proxy inbound ports (NOT behind the HTTP front):
     Hysteria2 (FAST1)  → UDP <port>            [LIVE: confirm]
     Shadowsocks (FAST2)→ TCP/UDP <port>        [LIVE: confirm]
     VLESS-Reality(Secure)→ 443/TCP via SNI front, or dedicated TCP <port>  [LIVE decision]
```

- Control-plane subdomains keep the [DOMAINS.md](DOMAINS.md) plan; `node-de.unseen.click` is the DE node's own host.
- Subscriptions are still served to customers **only** as `https://sub.unseen.click/s/<token>` by the Master sidecar;
  the node's raw Hiddify sub URL is internal (Master-to-node fetch). The front terminator must keep `access_log off`
  on the `/s/` path.

## Live verification checklist (run AFTER snapshot, BEFORE API coding)

1. Pin the install method/version; install on the snapshotted Master (or a throwaway 24.04 sandbox first).
2. From a second SSH session, confirm **SSH:22 still reachable** post-install.
3. `ss -tulpn` — record **actual** panel/subscription/Reality/Hysteria2/SS port numbers and binds.
4. Confirm 443 ownership matches the chosen option; control-plane subdomains still serve.
5. Pull the panel's **Swagger/OpenAPI** (Settings → API) → fill the API_CONTRACT **[LIVE]** fields/paths/units.
6. Confirm units (GB vs GiB) and reconcile with the Master's `data_limit_gib`.
7. Create one **disposable** test user via API v2; fetch its sub; import into Hiddify App on a real device; connect
   FAST1/FAST2/Secure; verify DE egress. (This is the §34 Phase-2 exit gate; node stays `status=test`.)
8. Confirm Hiddify's iptables didn't break the control plane or close intended ports.

## API v2 contract placeholders (verified-so-far)

Recorded in [HIDDIFY_API_CONTRACT.md](HIDDIFY_API_CONTRACT.md):
- **[VERIFIED]** Base shapes: admin `…/<admin_proxy_path>/api/v2/admin/…`, panel `…/<admin_proxy_path>/api/v2/panel/…`,
  user `…/<user_proxy_path>/api/v2/user/…`. Auth header `Hiddify-API-Key: <UUID>` (admin or user UUID; **treat as a secret**).
  Always v2 (v1 deprecating).
- **[LIVE]** exact user create/update/get/list/disable paths; field names/types (`usage_limit_GB`, `package_days`,
  `current_usage_GB`, `start_date`, `mode`, `enable`, `telegram_id`, `comment`); units; subscription endpoint/format.

## Readiness decision

**PARTIAL / HOLD.** The audit *plan* is complete and source-backed (this doc). **Install remains on HOLD** until:
(1) Charles chooses **Option A (co-locate via Docker)** or **Option C (separate DE VPS)**; (2) the **B2 provider snapshot**
is taken & confirmed; (3) the **live verification checklist** is executed on the snapshot/sandbox. No Hiddify code may be
written against the API until step 5–7 produce a verified contract.

## Live-verify status (2026-06-15)

Snapshot confirmed; co-location-via-Docker chosen; safety gate PASSED. Per decision the **operator runs the install**
and the agent verifies after — see [PHASE3_HIDDIFY_LIVE_VERIFY.md](PHASE3_HIDDIFY_LIVE_VERIFY.md). New official finding:
the current Docker install is `bash <(curl https://i.hiddify.com/docker/<version>)` and Hiddify labels the Docker
version **"not recommended for permanent use"** — fine for the test node, but reinforces revisiting **Option C
(separate DE VPS, host install on 22.04)** for a *live* DE node.

## Exact next recommended task

**Decision + snapshot, then a sandbox live-verify.** Recommended sequence:
1. **Charles decides** co-location (Option A) vs separate DE VPS (Option C), and **takes/confirms the B2 snapshot**.
2. A separate **"Phase 3 live-verify"** task installs the pinned Hiddify on the snapshotted Master (Option A) or a
   throwaway 24.04 sandbox, runs the live checklist, and fills the **[LIVE]** API/port fields.
3. Only then does Phase 4 (DB/backend) wire the orchestrator against the **verified** contract.

# UNSEEN PROXY — SOURCE OF TRUTH (consolidated, auto-generated)

> **Generated:** 2026-06-16T02:54:04Z — by `scripts/build_source_of_truth.sh`.
> **This is the live project state for external readers (e.g. the Custom GPT).** It is DERIVED from the
> canonical docs below and regenerated each task. Upload THIS file to the GPT (not IMPLEMENTATION_PLAN.md,
> which is the static v1.9 plan). Re-download after updates.

## How the canonical docs relate
- `IMPLEMENTATION_PLAN.md` — static v1.9 **plan/intent** (not updated as work proceeds).
- `docs/DECISIONS.md` — **ADRs that SUPERSEDE the plan** where they differ (authoritative).
- `docs/CURRENT_STATUS.md` — **live phase tracker + next task**.
- `docs/CHANGELOG.md` — chronological record of what changed.
- `docs/HIDDIFY_API_CONTRACT.md` — verified Hiddify API v2 contract.
- Other `docs/*.md` — architecture, security, nodes, regions, protocols, etc.

## Non-negotiable invariants (from the plan + ADRs)
- **Clean-build isolation:** build only from this project; never reference the retired UNSEEN VPN/Marzban/Happ.
- **Master = control-plane only;** it carries NO proxy traffic (co-location RETIRED — ADR-001).
- **Dynamic config:** plans/prices/caps/durations/regions/protocols/nodes are DB-driven, never hardcoded.
- **Secrets never exposed/committed;** `.env` only, git-ignored + pre-commit secret scan.
- **Not all regions/protocols live by default;** each enabled only after a node test. Nodes start `status=test`.
- **Dry-run first; live actions double-gated** (env latch + `--live --confirm`). Never fabricate a PASS.
- **Hiddify uses GB**; UNSEEN stores GiB — convert GiB↔GB at the orchestrator.
- **Burmese-primary frontend** (~90% Burmese / English terms); invoices/receipts in English; no email/password.


---

# CURRENT STATUS (docs/CURRENT_STATUS.md)

# CURRENT STATUS

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §34
> **Status:** live phase tracker; updated as phases progress

Where the UNSEEN PROXY build stands across the §34 deployment phases.

## Phase tracker

| Phase | Title | Status |
|---|---|---|
| 0 | Clean-VPS verification (gate before any build) | DONE (gate passed) |
| 1 | Documentation, repo & architecture planning | DONE (pushed to origin/main, 25e5ddc) |
| 2 | Hiddify test node setup | **RE-SCOPED to a separate DE VPS** (`de1`, `5.249.160.59`, Ubuntu 22.04, planned/test). Master-co-location preflight done then RETIRED. Forward plan: PHASE2_3_DE_NODE_PLAN.md |
| 3 | Hiddify API & subscription compatibility audit | **DONE (PASS w/ follow-ups) — Hiddify v12.3.3 on de1; API v2 contract VERIFIED-LIVE; disposable test user create→sub→delete confirmed.** Phase 4 API layer UNBLOCKED. Node-tuning follow-ups: SS:8388/UDP reachability, RAM lock, SSH hardening, regenerate leaked default-user keys. See HIDDIFY_API_CONTRACT.md + PHASE3_DE1_HIDDIFY_LIVE_VERIFY.md |
| 4 | Database & backend clone design | **NEXT — now unblocked** (build against the verified contract; remember GiB↔GB) |
| 5 | Telegram bot implementation (Burmese-primary) | PENDING |
| 6 | Hiddify subscription delivery integration | PENDING |
| 7 | Plan-based region/protocol entitlement + node resilience | PENDING |
| 8 | Web app / customer portal | PENDING |
| 9 | Messenger and Viber bot integration | PENDING |
| 10 | Monitoring, backup, security, production hardening | PENDING |
| 11 | Internal beta testing | PENDING |
| 12 | Controlled public soft launch | PENDING |

## Next up

**Architecture (current):** the **Master is control-plane only** — co-location is **retired**
([DECISIONS.md](DECISIONS.md) ADR-001). The Master was tested as a co-located DE node via Hiddify's experimental
Docker (v12.3.3); the panel was non-functional (compose `$REDIS_PASSWORD` bug + DB migration errors), so it was torn
down and the Master returned to baseline (SSH up, 80/443 free, Docker engine left installed but unused — a **cleanup
candidate** per [DECISIONS.md](DECISIONS.md) ADR-003, to be removed in a future audited "Master cleanup" task).

**DE node is now a dedicated separate VPS:** `de1`, `5.249.160.59`, 4 vCPU / 4 GB / 25 GB SSD / 30 TB, **Ubuntu
22.04 LTS**, `status=test`, domain `node-de.unseen.click` — managed from the Master only, proxy traffic only.
These specs are **provider estimates (unverified)**; per [DECISIONS.md](DECISIONS.md) ADR-002 the Master detects the
node's real facts (read-only) at preflight and those override the estimates.

**SSH key prepared (2026-06-15):** a dedicated Master→`de1` ed25519 keypair exists at
`/root/.ssh/unseenproxy_de1_ed25519` (private `600`, root-only) / `.pub` (`644`), comment `unseen-proxy-master-to-de1`,
fingerprint `SHA256:jUYAdY0ONdXKzOg2s4OKO27yBGqLvBwapkEy25oA3+I`.

**Phase 2-DE preflight (2026-06-15) — PARTIAL.** Root key SSH now **works** (Charles installed the key). Read-only
preflight ran: `de1` is **clean** (no legacy/proxy artifacts, no nginx/docker/certbot, only SSH:22 public, no
firewall), CPU 4 ✓, disk 25 GB ✓, public IP `5.249.160.59` ✓, RAM **3.1 GiB** (vs 4 GB estimate). **BLOCKER: OS is
Ubuntu 20.04.6, not the required 22.04.**

**✅ de1 is back on Ubuntu 22.04.5 (re-verified 2026-06-15T18:57Z).** Charles reinstalled to 22.04.5 live-server, fixed
networking, and re-added the Master key. Re-verify: **SSH root key works** (host key changed by reinstall → refreshed),
**OS 22.04.5 LTS** ✓, node **clean**, **ufw active** (SSH allowed), network **persistent** (static netplan, `ens18`).
**Resolved:** root LV **23 GB (17 GB free)**; DNS `node-de.unseen.click` added; network persistent across reboot.

**Phase 3-DE (2026-06-16) — Hiddify v12.3.3 INSTALLED & RUNNING on de1; result PARTIAL.** Charles accepted the RAM
risk and we proceeded. Installed via the official **host** installer (`v12.3.3 --no-gui`, not Docker). All services
active (panel/nginx/haproxy/xray/singbox/mariadb); **443 up**; **FAST1(Hysteria2)/FAST2(Shadowsocks)/Secure(VLESS-Reality)
inbounds present**; admin link secured at `/root/hiddify-de1-admin.link` (0600, never printed); SSH safe; ufw active.
RAM is balloon-dynamic — idle ~1.8 GiB but **deflated to ~3.8 GiB under load, no OOM**. (Note: the first install hit a
permission cascade caused by the agent's `umask 077` at launch + uv cache hardlinks — fully remediated; lesson recorded.)
**Deferred (blocks Phase 4):** exact API v2 CRUD paths/fields/units + disposable test user — the v12.3.3 API path wasn't
black-box-discoverable (probes hit Hiddify's decoy site) and the OpenAPI route errors (likely the marshmallow-v4 bug).
Detail: [PHASE3_DE1_HIDDIFY_LIVE_VERIFY.md](PHASE3_DE1_HIDDIFY_LIVE_VERIFY.md).

**Update (2026-06-16T02:37Z): API contract VERIFIED-LIVE; Phase 3-DE = PASS (w/ follow-ups).** The OpenAPI spec builds
fine in-process (the earlier HTTP failures were a wrong-proxy_path decoy, not the marshmallow bug → **no package
change**). Full contract captured in `HIDDIFY_API_CONTRACT.md` (endpoints, fields, **units = GB**, sub endpoints); a
disposable-test user was created→verified→sub-checked→deleted (re-GET 404). **Phase 4 API layer is UNBLOCKED.**

**Next: Phase 4** (DB/backend + orchestrator) against the verified contract — convert **GiB↔GB**. Node-tuning before
live (non-blocking): proxy-port reachability (SS:8388/UDP via ufw), real-device connect test, lock 4 GB RAM, disable
SSH password login, regenerate the leaked default-user/server keys. Node stays `status=test`.

**OS path decided (2026-06-15):** in-place `do-release-upgrade` was considered, but since `de1` is **empty** the
safer, same-outcome choice is a **clean provider reinstall to Ubuntu 22.04** (Charles). A read-only pre-upgrade gate
passed; **no in-place upgrade was run** (no node changes). → Charles reinstalls to 22.04, **re-adds the Master public
key** to root `authorized_keys` (reinstall wipes it), then we **re-run preflight** before Phase 3-DE. (Reinstall
changes the node host key — the Master refreshes `known_hosts` for `5.249.160.59` on next connect; the mismatch
warning is expected.) Reports: [PHASE2_DE1_OS_UPGRADE.md](PHASE2_DE1_OS_UPGRADE.md),
[PHASE2_DE1_PREFLIGHT.md](PHASE2_DE1_PREFLIGHT.md).

**Next task — Phase 2-DE / 3-DE** (see [PHASE2_3_DE_NODE_PLAN.md](PHASE2_3_DE_NODE_PLAN.md)): clean-VPS preflight on
`de1` (verify 22.04, no legacy, ports/firewall/resources, DNS plan), Master→node SSH key setup, then Hiddify's
**supported host install**, live Swagger/API-contract verification, one disposable test user, and FAST1/FAST2/Secure
inbound checks. **No connection to the node yet** — that's the next authorized task. **Phase 4 stays blocked** until
the DE node yields a verified-live API contract.


---

# DECISIONS / ADRs (docs/DECISIONS.md)

# DECISIONS — Architecture Decision Record (ADR) log

> **Purpose:** durable record of architectural decisions that **supersede or refine** parts of
> [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md). The plan is kept as **source-history** (not edited per-decision);
> where this log and the plan differ, **this log wins** for the named section.

---

## ADR-001 — Master is control-plane-only; DE Hiddify node moves to a separate VPS (co-location retired)

- **Date:** 2026-06-15
- **Status:** ACCEPTED (Charles)
- **Supersedes:** IMPLEMENTATION_PLAN.md **§4.1 co-location exception** (DE node co-located on the Master) — **retired for this build.**

### Context

The plan's §4.1 allowed one deliberate exception: the Master (control plane) would also host the DE Hiddify node to
save a VPS. Phase 2 preflight + Phase 3 audit prepared this, and Phase 3 live-verify **attempted it** with Hiddify's
official pinned **Docker** install (v12.3.3) on the Ubuntu-24.04 Master.

### What happened (evidence)

- The Docker stack came up (containers running; host stayed safe — SSH up, control plane intact, isolated to
  `/opt/hiddify-manager`), **but the panel never served** (443 → no response).
- **Root cause (confirmed at teardown):** the experimental `docker-compose.yml` interpolates `$REDIS_PASSWORD` from
  the compose project `.env`/shell — **not** from the `env_file: docker.env` where the installer writes it. So Redis
  started with a **blank** password while the panel authenticated *with* one → `redis.exceptions.AuthenticationError`,
  which cascaded into the panel failing to start. First-boot DB migration errors and a hanging `hiddifypanel` CLI
  compounded it.
- This matches Hiddify's **official caveat** that the Docker version is *"experimental / not recommended for permanent use."*
- The broken stack was torn down (`docker compose down -v` + dir removed); the Master returned to baseline
  (SSH up, 80/443 free, iptables INPUT `ACCEPT`; Docker engine left installed but unused).

### Decision

1. **The Master VPS is CONTROL-PLANE ONLY.** It never carries proxy traffic. It runs: bots, the unified DB, payments,
   admin, customer portal, API, the subscription sidecar, monitoring, backups, Git-based deployment, and node
   orchestration. Its specs are not "wasted" — they protect the business/control plane.
2. **The DE Hiddify node moves to a separate, dedicated VPS** (details in [SERVERS.md](SERVERS.md)), provisioned with
   Hiddify's **supported host installer on Ubuntu 22.04 LTS** (not Docker, not on the Master).
3. **Hiddify-Docker-on-Master is NOT a viable path for this build** and will not be retried; Docker on the Master is
   left installed but unused (removal deferred unless Charles asks).
4. The DE node starts **`planned`/`test`**, never auto-promoted to `live`, carries **no** customer/business data, and is
   **managed only from the Master** over Hiddify API v2.

### Consequences

- The "Master never proxies" rule is now **absolute** — no co-location exception anywhere in this build.
- DE becomes an **ordinary dynamic node** (§6.1): pure data in `proxy_nodes`, replaceable by a row update.
- **Phase 4 (DB/backend orchestrator) remains BLOCKED** until the Hiddify API v2 contract is **verified live** on the
  new DE node (see [PHASE2_3_DE_NODE_PLAN.md](PHASE2_3_DE_NODE_PLAN.md)).
- Affected docs updated: ARCHITECTURE, SYSTEM_OVERVIEW, SERVERS, NODES, NETWORK, PORTS, DEPLOYMENT, ROLLBACK,
  SECURITY, HIDDIFY_API_CONTRACT, the PHASE2/PHASE3 docs, CURRENT_STATUS, CHANGELOG.

---

## ADR-002 — Provider/purchase specs are ESTIMATES; the Master must verify actual node facts on onboarding

- **Date:** 2026-06-15
- **Status:** ACCEPTED (Charles) — **requirement for the future node-preflight phase; not executed now.**

### Context

Node specs/limits in our docs (e.g. `de1`: 4 vCPU / 4 GB / 25 GB / 30 TB / Ubuntu 22.04) currently come **only** from
the provider/purchase page. These are **expected values**, not measured facts — a provider page can be rounded,
mislabelled, or differ from what the OS actually reports (CPU count, usable disk after the image, real RAM, the OS
version actually installed, the bandwidth cap the provider truly enforces).

### Decision

1. **Treat all pre-provided specs as preliminary estimates only.** The Master **must not blindly trust** manually
   entered/purchase specs for operational decisions.
2. **On node onboarding (the real preflight phase), the Master collects actual node facts** directly from the node via
   **read-only SSH probes** — never mutating the node, never printing secrets.
3. **Detected facts override estimates** in operational docs/status and (later) in the DB node metadata.
4. **Every spec value carries a provenance tier:**
   - `estimate` — provider/purchase value (unverified)
   - `detected` — read by the Master from the node itself (authoritative for hardware/OS/ports)
   - `provider-confirmed` — from a provider API/dashboard (e.g. the real bandwidth allowance), where available
   - `unknown` — not yet verified
   Bandwidth allowance stays **`estimate`** until **`provider-confirmed`** (the node can't self-report its contractual cap).
5. **Verify before Hiddify install, and re-check after install** if resource usage materially changes.
6. **Role-fit gate:** the preflight must confirm detected resources meet the node's role (enough disk/RAM for Hiddify)
   and that the node is clean of legacy artifacts, before any install proceeds.

### Consequences

- The future probe (read-only, no-secrets, no-mutation) is specified in
  [PHASE2_3_DE_NODE_PLAN.md](PHASE2_3_DE_NODE_PLAN.md); suggested name `scripts/node_preflight_probe.sh`. It is
  **written/run only when Phase 2-DE actually begins** — not now.
- Operational docs ([SERVERS.md](SERVERS.md), [NODES.md](NODES.md)) now label `de1`'s specs as **provider-estimate
  (unverified)** and reserve a place for detected/confirmed values.
- When the DB schema exists (Phase 4), `proxy_nodes` should store both the estimate and the detected value (or a
  provenance flag per field) rather than a single unqualified number.

---

## ADR-003 — Master minimalism and cleanup of abandoned co-location dependencies

- **Date:** 2026-06-15
- **Status:** ACCEPTED (Charles) — **future requirement; NOT executed now.**
- **Relates to:** ADR-001 (co-location retired).

### Decision

The **Master is control-plane only.** Any package/service/feature installed **solely** for the abandoned co-located
DE-Hiddify path is a **cleanup candidate**. In particular, the **Docker engine** remains installed only as a leftover
from the failed Hiddify-on-Master test (ADR-001); if no control-plane task needs it, it should be **removed in a
future audited cleanup task**, *not* during node onboarding.

### Rationale

Unused infrastructure packages add attack surface, maintenance burden, port/firewall confusion, and operational
drift. The Master should run **only** what the control plane needs: bots, DB, payments, admin, customer portal, API,
the subscription sidecar, monitoring, backups, Git-based deployment, and node orchestration.

### Future cleanup task — "Master cleanup after retired co-location attempt"

Done in a **safe, audited phase of its own** (not during node onboarding). **Pre-removal verification (all must hold):**
- no running containers; no Docker volumes/networks/images that are needed;
- no project **service** depends on Docker; no **docs/scripts** currently require Docker;
- no Hiddify remnants remain on the Master (no `/opt/hiddify-manager`, no hiddify units/images);
- Master **80/443 remain free**; **SSH untouched**.

**If safe, may remove:** the unused Docker engine/packages; unused Docker networks/volumes/images; any abandoned
Hiddify-on-Master remnants; any other package/service installed only for the retired co-location path.

**Safety:** consider a provider snapshot — or at minimum a **git-clean tree + a recorded service/package-state
backup** — before host package removal. Removal steps are dry-run/audited; **stop and report** on any unexpected
dependency. Update docs + commit/push afterward.

### Current state (for the cleanup task to act on)

Docker **29.5.3** is installed and **idle** (no Hiddify; `/opt/hiddify-manager` already removed; 80/443 free) — it is
the primary cleanup candidate. Left installed for now per ADR-001; removal deferred to the audited cleanup task above.


---

# VERIFIED HIDDIFY API CONTRACT (head of docs/HIDDIFY_API_CONTRACT.md)

# HIDDIFY API CONTRACT

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §14.1, Appendix C, §34 (Phase 3)
> **Status:** Phase 3 audit (docs) — base/auth **verified from official docs**; CRUD/fields/units **need live Swagger**.
> Tiers: **[VERIFIED]** official docs · **[LIVE]** confirm on a real install · **[ASSUMPTION]** do not depend yet.
> See [PHASE3_HIDDIFY_AUDIT_PLAN.md](PHASE3_HIDDIFY_AUDIT_PLAN.md).
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



---

# RECENT CHANGELOG (head of docs/CHANGELOG.md)

# CHANGELOG

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §32, §34
> **Status:** Phase 1 skeleton — running log of changes by date

Chronological record of notable changes to the UNSEEN PROXY project.

## 2026-06-16 — Phase 3-DE follow-up: API v2 contract VERIFIED-LIVE; disposable user OK — PASS (w/ follow-ups)

- **API contract recovered & verified.** The earlier OpenAPI HTTP failures were **routing/decoy** (wrong proxy_path),
  **not** the marshmallow-v4 bug — the spec builds fine in-process (22 paths). **No package change made.** Used the
  authoritative proxy_path (`hiddifypanel admin-path`) to verify live.
- **VERIFIED-LIVE (`HIDDIFY_API_CONTRACT.md`):** Hiddify v12.3.3, API "Hiddify API v2.2.0"; auth `Hiddify-API-Key:
  <admin-UUID>` header; user CRUD `GET|POST /admin/user/`, `GET|PATCH|DELETE /admin/user/{uuid}/`; fields incl.
  `usage_limit_GB`/`current_usage_GB` (**units = GB → orchestrator must convert GiB↔GB**), `package_days`, `start_date`,
  `enable`, etc.; subscription via `/user/all-configs/`, `/user/me/`.
- **Disposable test user:** created (`disposable-test`, 1 GB / 1 day) → GET 200 → all-configs 200 (~14.8 KB) → DELETE
  200 → re-GET 404. Clean. Users back to 1.
- **Reachability (from Master):** tcp 22/80/443 OPEN (443 TLS 200); **8388 (SS) filtered**, UDP needs device test;
  ufw active (22 + 4 Hiddify proxy ACCEPT rules). SSH safe throughout.
- **⚠ Secret-safety incident (disclosed, not committed):** a shell-quoting bug printed an API response to the terminal,
  exposing the Hiddify **default** user's ed25519/WireGuard keys (no-customer test node; never entered git). Fixed
  process (bodies→files, UA quoted). Remediation: regenerate default-user/server keys before live (or on rebuild).
- **Phase 4 API layer UNBLOCKED.** Updated HIDDIFY_API_CONTRACT/PHASE3_DE1/CURRENT_STATUS/NODES/SERVERS/PORTS/NETWORK/
  SECURITY. Node stays `status=test`; no package/OS changes; no real customers.

## 2026-06-16 — Phase 3-DE: Hiddify v12.3.3 installed & running on de1 — PARTIAL (API contract deferred)

- Charles accepted the low-RAM risk; proceeded. Installed Hiddify Manager **v12.3.3** via the official **host**
  installer (`download.sh v12.3.3 --no-gui`, non-interactive, NOT Docker, version-pinned).
- **All services active** (panel/nginx/haproxy/xray/singbox/mariadb); **443 tcp+udp up**; **FAST1(Hysteria2)/
  FAST2(Shadowsocks, :8388)/Secure(VLESS-Reality) inbounds present**; SSH safe; ufw active (22 allowed); admin link
  stored at `/root/hiddify-de1-admin.link` (0600, never printed). API title **Hiddify v2.2.0**; auth header
  `Hiddify-API-Key: <admin-UUID>`.
- **Permission cascade (transparent):** first install failed to start — root cause was the agent's **`umask 077`** at
  launch (made installer dirs 700 + poisoned uv's cache with 600 files that uv hardlinks into the venv). Remediated:
  reinstall under `umask 022` + `chmod -R a+rX /usr/local/share/uv` + `chmod -R a+rX .venv313` → panel active +
  apply_configs regenerated all services. Lesson: never set a restrictive umask when launching third-party installers.
- RAM balloon-dynamic: ~1.8 GiB idle → ~3.8 GiB under load, no OOM.
- **Deferred (blocks Phase 4):** exact API v2 CRUD paths/fields/units + disposable test user — v12.3.3 API path not
  black-box-discoverable (probes hit Hiddify's decoy site); OpenAPI route errors (likely marshmallow-v4 bug). Capture
  via browser Swagger or fix the spec route. New `PHASE3_DE1_HIDDIFY_LIVE_VERIFY.md`; updated HIDDIFY_API_CONTRACT/
  CURRENT_STATUS/NODES/SERVERS/PORTS/NETWORK/SECURITY/DEPLOYMENT/ROLLBACK. Node stays `status=test`.

## 2026-06-15 — Phase 3-DE: pre-install gate HOLD — RAM still ~1.8 GiB (Hiddify NOT installed)

- Ran the Phase 3-DE pre-install gate on de1. **All gates PASS except RAM.** OS 22.04.5 ✓, disk 23 GB/17 free ✓,
  network static + egress 5.249.160.59 ✓, **DNS `node-de.unseen.click` → 5.249.160.59 resolves (Master + node) ✓**,
  ufw active + 22/tcp allowed ✓, 80/443 free ✓, clean ✓.
- **RAM re-detect: still ~1.8 GiB** (`MemTotal 1908140 kB`) despite "disable ballooning" — node **not power-cycled**
  (uptime ~1h31m); the change needs a full **VM stop→start**, not a soft reboot. Per the gate, **STOPPED — Hiddify
  not installed, no node changes.**
- New `PHASE3_DE1_HIDDIFY_LIVE_VERIFY.md` (HOLD result + operator power-cycle step + pending contract fields);
  updated PHASE2_DE1_PREFLIGHT/CURRENT_STATUS. Docs only.

## 2026-06-15 — Phase 2-DE: extend de1 root volume (+ reboot/DNS resolved)

- **Authorized node change on `de1`:** safety gate PASS (SSH root key; OS 22.04.5; `/` = ext4 on
  `/dev/mapper/ubuntu--vg-ubuntu--lv`; LV path `/dev/ubuntu-vg/ubuntu-lv`; VG free 11.5 GB). Ran `lvextend -l
  +100%FREE` then online `resize2fs`. **Root `/` 12 GB → 23 GB (5.6 GB → 17 GB free)**; VG now fully allocated. No
  reboot, no firewall/SSH/Hiddify changes.
- **Network persistence CONFIRMED across reboot** (de1 came back; host key unchanged; static netplan `ens18` +
  default route up automatically).
- **DNS resolved:** `node-de.unseen.click → 5.249.160.59` A record added (Charles).
- **Still open:** RAM detected **1.8 GiB** vs 4 GB purchased — pending provider clarification. Updated
  PHASE2_DE1_PREFLIGHT/PHASE2_3_DE_NODE_PLAN/SERVERS/NODES/CURRENT_STATUS. Docs committed; Hiddify NOT installed.

## 2026-06-15 — Phase 2-DE: de1 re-verified on Ubuntu 22.04.5 — PARTIAL (resource items)

- de1 reinstalled to **Ubuntu 22.04.5 LTS** (Charles); networking fixed; Master key re-added. Host key changed by
  reinstall → removed only the de1 `known_hosts` entry and re-pinned (expected).
- Re-ran read-only preflight: **SSH root key works**; **OS 22.04.5** (kernel 5.15) ✓; hostname `de1`; **clean** (no
  legacy/proxy/nginx/docker); only SSH:22 public, 80/443 free; **ufw ACTIVE** (INPUT DROP, SSH allowed); egress
  `5.249.160.59` ✓.
- **Network persistence = PASS:** static `/etc/netplan/01-netcfg.yaml` for `ens18` (dhcp4 off, static IP+route),
  systemd-networkd-managed, **no manual dhclient**, cloud-init not overriding → survives reboot.
- **Detected vs estimate:** OS ✓, CPU 4 ✓, IP ✓; **RAM 1.8 GiB** (vs 4 GB purchased *and* prior 3.1 GiB — investigate);
  **root LV ~12 GB / 5.6 GB free** of 25 GB disk (~11.5 GB unallocated VG → extend before Hiddify).
- **Result PARTIAL.** Before Phase 3-DE: extend root LV, clarify RAM with provider, add `node-de.unseen.click` A
  record. Updated PHASE2_DE1_PREFLIGHT (rewritten for 22.04) + OS_UPGRADE/SERVERS/NODES/NETWORK/PORTS/SECURITY/
  CURRENT_STATUS. Docs only; node changes = none (read-only).

## 2026-06-15 — Phase 2-DE: de1 OFFLINE after custom-ISO attempt — upgrade on HOLD

- Tried to diagnose/fix de1's release-upgrade connectivity (`changelogs.ubuntu.com` unreachable on console after a
  custom-ISO attempt). From the Master, **de1 is now fully unreachable**: 100% ICMP loss; TCP 22/1022/80/443 all
  timeout; SSH connect timed out. **Whole node offline**, not a DNS/CA issue.
- Per the task Step-1 rule, **STOPPED** — cannot SSH in to diagnose/fix; no node changes, no upgrade run.
- **Recovery = operator/console:** check de1 boot state in the provider panel; **reinstall to Ubuntu 22.04 LTS (EN)**
  with the Master public key added (recommended; node is empty). Then re-test + re-run preflight. Updated


---

# SERVER / NODE INVENTORY (head of docs/SERVERS.md)

# SERVERS

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) Appendix F.7
> **Status:** Phase 1 skeleton — decided from plan

Current server inventory (recorded 2026-06-15). These seed the `proxy_nodes` rows. **Specs and addresses are data, not code** — replacing or moving any node is a row update (§6.1). The public IP is stored in `proxy_nodes.public_ip`; the **panel API key and secret admin path live only in `.env`**, referenced by handle. Nodes seed as `planned`/`test` and are promoted to `live` only after the node-verification gate.

## Master VPS (control plane ONLY)

> **Co-location retired** — see [DECISIONS.md](DECISIONS.md) ADR-001. The Master no longer hosts the DE node and
> **carries no proxy traffic**. It runs the control plane only: bots, DB, payments, admin, portal, API, the
> subscription sidecar, monitoring, backups, Git deployment, and node orchestration. Its specs are not "wasted" —
> they protect the business/control plane.

| Field | Value |
|---|---|
| Role | **Master / control plane only** (no Hiddify, no proxy traffic) |
| Region (hosted in) | Germany |
| Public IP | `88.214.56.96` |
| Spec | 4 vCPU, 16 GB RAM, 100 GB SSD |
| Bandwidth budget | 30 TB / month |
| Note | NOT a `proxy_nodes` row (it is the control plane, not a node). Docker engine remains installed but **unused** — a **cleanup candidate** per [DECISIONS.md](DECISIONS.md) ADR-003 (removed in a future audited cleanup task if no control-plane need). |

**Master history (2026-06-15):** the Master is Ubuntu 24.04.4 (`crimson-gorilla-49484`, KVM/QEMU; 4 vCPU Xeon
E5-2680 v4, ~13 GiB RAM free, 4 GiB swap, 86 GB disk free). A co-location attempt installed Hiddify via Docker
(v12.3.3) here; the panel was non-functional (compose Redis-password bug + DB migration errors) and was **torn down**
— the Master is back to baseline (SSH up, 80/443 free; Docker engine left installed but unused). Co-location is
**retired** ([DECISIONS.md](DECISIONS.md) ADR-001); the Master is control-plane-only henceforth.

## Proxy nodes (data plane)

| node_code | region | Public IP | vCPU | RAM | Disk | Bandwidth budget | Status | OS |
|---|---|---|---|---|---|---|---|---|
| `de1` | DE | `5.249.160.59` | 4 | 4 GB | 25 GB SSD | 30 TB/mo | **planned/test** | Ubuntu 22.04 LTS |
| `sg1` | SG | `64.56.71.64` | 1 | 2 GB | 60 GB SSD | 10 TB/mo | planned | — |
| `sg2` | SG | `104.250.118.37` | 1 | 2 GB | 20 GB SSD | 2 TB/mo | planned | — |
| `us1` | US | `172.245.110.130` | 5 | 6 GB | 100 GB SSD | 9.8 TB/mo | planned | — |

**`de1` (new, 2026-06-15):** the dedicated DE Hiddify node replacing the retired Master co-location — the
**default/entry region** now lives here. Seed: `node_code=de1`, `region_code=de`, `public_ip=5.249.160.59`,
`vcpu_count=4`, `ram_mb=4096`, `disk_gb=25`, `bandwidth_budget_gb=30000`, `status=test`. To be provisioned by
Hiddify's **supported host installer on Ubuntu 22.04** (not Docker, not on the Master) — see
[PHASE2_3_DE_NODE_PLAN.md](PHASE2_3_DE_NODE_PLAN.md). Node domain `node-de.unseen.click`.

> **These values were provider/purchase ESTIMATES; preflight has now DETECTED actuals (2026-06-15).** Per
> [DECISIONS.md](DECISIONS.md) ADR-002 the detected values are authoritative. Full report:
> [PHASE2_DE1_PREFLIGHT.md](PHASE2_DE1_PREFLIGHT.md).
>
> | Field | Estimate | **Detected (2026-06-15, after 22.04 reinstall)** | Provenance |
> |---|---|---|---|
> | OS | Ubuntu 22.04 | **Ubuntu 22.04.5 LTS** (kernel 5.15) ✓ | detected |
> | vCPU | 4 | 4 (Xeon E5-2690 v4) ✓ | detected |
> | RAM | 4 GB | **1.8 GiB** (+2.1 GiB swap) ⚠ under estimate — clarify w/ provider | detected |
> | Disk (raw) | 25 GB | 25 GB `sda` ✓ | detected |
> | Disk (usable `/`) | — | **23 GB LV, 17 GB free** (extended 2026-06-15; VG fully allocated) ✓ | detected |
> | Public IP | 5.249.160.59 | 5.249.160.59 (`ens18` + egress) ✓ | detected |
> | Bandwidth | 30 TB/mo | not node-detectable | estimate (unconfirmed) |
>
> Hostname `de1`. Node is **clean** (no legacy/proxy artifacts; only SSH:22 public; no nginx/docker); **ufw active**;
> network **persistent** (static netplan for `ens18`). **Hiddify v12.3.3 installed & running (2026-06-16)** — host


---

_End of consolidated source of truth. Regenerate with \`bash scripts/build_source_of_truth.sh\`._

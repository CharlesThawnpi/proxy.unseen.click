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
| 4 | Database & backend clone design | **Phase 4A DONE (dry-run/test-safe): migrations + schema + seed + Hiddify client + provisioner CLI + 17 tests PASS.** No live mutations. See PHASE4A_DB_BACKEND_FOUNDATION.md. Next: Phase 4B (services/idempotency/queue/backup). |
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

**Phase 4A complete (2026-06-16):** stdlib backend foundation — `backend/` (db/migrate/seed/units/customer_code/
display/config + `hiddify/client.py`), `bin/init_db.py` + `bin/hiddify_customer_provisioner.py` (dry-run; live
double-gated), `tests/` (17 PASS). Seeded plans/regions/protocols/entitlements + de1 (`status=test`). No live Hiddify
calls, no real customers, no services started.

**GPT tooling:** `SOURCE_OF_TRUTH.md` is the file to upload to the Custom GPT (auto-generated). **Brain API** =
design-only ([BRAIN_API_DESIGN.md](BRAIN_API_DESIGN.md)); build is a separate gated task.

**Next: Phase 4B** — AccountService/NotificationService boundaries, idempotency on payment-approval/provision, the
outbound-notification queue, and a WAL-safe online-backup script (still dry-run for Hiddify). **de1 pre-live tuning**
(SS:8388/UDP ports, RAM lock, SSH hardening, regenerate leaked default-user keys) remains before any live provisioning.

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

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
| 3 | Hiddify API & subscription compatibility audit | **DONE (PASS) — Hiddify v12.3.3 on de1; API v2 contract VERIFIED-LIVE; disposable test user create→sub→delete confirmed.** Phase 4 API layer UNBLOCKED. **Re-verified after a fresh de1 rebuild + clean reinstall (2026-06-16, PHASE9_DE1_REBUILD_FRESH_HIDDIFY.md): contract re-confirmed (bounded `marshmallow==3.26.1` venv pin needed), disposable-user lifecycle PASS, FAST1/FAST2/Secure present, SSH hardened. `leaked_key_rebuild_pending` CLEARED.** **Node domain `node-de.unseen.click` now SET with a valid Let's Encrypt cert (2026-06-16): added via `hiddifypanel add-domain` + `apply_configs.sh`; API/all-configs verified-live over the public node-de path with valid TLS; subscription output now references `node-de.unseen.click` (resolves Phase 9 blocker #4).** **Real-device import (2026-06-16): two issues found+addressed. (1) Mobile `127.0.0.1:64127` = app-side core (server output clean). (2) Windows `[SingboxParser] ... outbounds[37].tunnel-per-resolver: json: unknown field` = generator↔parser mismatch from the DNSTT outbound — FIXED by disabling DNSTT (`set-setting dnstt_enable=false` + apply; DNSTT is not FAST1/FAST2/Secure). After-render confirms `tunnel-per-resolver`=0/dnstt=0; FAST1/Secure outbounds intact. Disposable user recreated DNSTT-free. Secondary (deferred): sub output still multi-domain (raw-IP/sslip won't connect; manual panel prune). Real-device retest can proceed once Charles re-imports the fresh node-de subscription on an updated app. (3) Hiddify's default profile was too broad (100 outbounds across raw-IP/sslip, no clean FAST1/FAST2/Secure) — PRUNED to a clean UNSEEN-only profile via supported `set-setting` + `sub_link_only`: now exactly hysteria2(FAST1)+shadowsocks(FAST2)+vless-Reality(Secure), all on node-de (FAST1 udp:14430, FAST2 :16753, Secure tcp:443+decoy SNI), no raw-IP/sslip/vmess/tuic/naive/mieru/ssh/wireguard, no tunnel-per-resolver/dnstt/private-keys (100→9 outbounds). Disposable user rotated (Charles pasted profile text). Protocols NOT yet PASS — awaits real-device connect.** Remaining: real-device FAST1/FAST2/Secure connect PASS + RAM lock. See HIDDIFY_API_CONTRACT.md + PHASE3_DE1_HIDDIFY_LIVE_VERIFY.md + PHASE9_DE1_REBUILD_FRESH_HIDDIFY.md |
| 4 | Database & backend clone design | **Phase 4A + 4B + 4C DONE (dry-run/test-safe).** 4A: migrations + schema + seed + Hiddify client + provisioner CLI. 4B: AccountService + account-link codes + NotificationService (queue-first) + idempotency + WAL-safe online backup (`0002`). 4C: dry-run provisioning orchestration — payment-approval boundary → subscription snapshots → access-profile placeholder → provisioning plan (entitlements + live blockers + sanitized Hiddify intent) → delivery enqueue → audit + forward-only compensation; **live hard-refused**; additive migration `0003`. **70 tests PASS**. No live mutations/sends/real customers. See PHASE4A/4B/4C docs. |
| 5 | Telegram bot implementation (Burmese-primary) | **Foundation + transport DONE (dry-run, gated).** Foundation: adapter + Burmese catalogue + router + AccountService identity + env-driven admin. Transport: Bot API boundary (token redacted; injectable opener), offset-tracked polling runner, NotificationService sender consuming `outbound_messages` (queued→sent/requeue/dead), fail-closed double gate. **No polling daemon/webhook/API/send; no systemd.** See PHASE5_TELEGRAM_BOT_FOUNDATION.md + PHASE5_TELEGRAM_TRANSPORT_FOUNDATION.md. Live bring-up = next, Charles-gated. |
| 6 | Hiddify subscription delivery integration | **Foundation DONE (dry-run): delivery payload model (safe refs only) + branded link rule (`sub.unseen.click/s/<token>`, hash stored) + deep-link/copy-link priority + QR planned + mocked Hiddify-output normalizer + NotificationService/Telegram render integration. No raw links persisted/logged; no network.** See PHASE6_SUBSCRIPTION_DELIVERY_FOUNDATION.md. Sidecar + live = next, gated. |
| 7 | Plan-based region/protocol entitlement + node resilience | **Foundation DONE (dry-run, DB-driven): `entitlements` (plan→region/protocol, FAST rule, safe errors) + `node_resilience` (status×health readiness, reason vocabulary, graceful degradation, data-driven `node_live_blockers`) + `availability` (region/protocol availability) + provisioning-plan integration + Burmese availability copy. Additive migration `0005`. No node live; no metrics fetch.** See PHASE7_ENTITLEMENT_NODE_RESILIENCE.md. Health monitor = next. |
| 8 | Web app / customer portal | **Foundation + 8A preview + 8B auth/session + 8C HTTP boundary DONE (render-only + local-only HTTP adapter, dry-run): compact responsive portal UI, sanitized preview export, hash-only portal access tokens/sessions, branded `/s/<opaque-token>` resolver boundary, route guards for private pages, plus a local-only HTTP request/response adapter + cookie/CSRF/rate-limit/access-log helpers + dry-run subscription sidecar. No server, no public endpoint, no nginx/TLS/systemd, no real cookie service, no live delivery, no Hiddify/Telegram network.** See PHASE8_WEB_PORTAL_FOUNDATION.md + PHASE8A_PORTAL_PREVIEW_REFINEMENT.md + PHASE8B_PORTAL_AUTH_SESSION_FOUNDATION.md + PHASE8C_PORTAL_HTTP_DEPLOYMENT_BOUNDARY.md + PORTAL.md. |
| 9 | Messenger and Viber bot integration | PENDING |
| 10 | Monitoring, backup, security, production hardening | PENDING |
| 11 | Internal beta testing | PENDING |
| 12 | Controlled public soft launch | PENDING |

## Next up

**Timezone policy accepted (2026-06-16 MMT)** ([TIMEZONE_POLICY.md](TIMEZONE_POLICY.md), [DECISIONS.md](DECISIONS.md)
ADR-004): all business/customer/project dates use Myanmar Time (**MMT**, UTC+06:30, `Asia/Yangon`). External UTC must
be converted before customer/business use; technical UTC fields must be explicitly labeled. Helper module:
`backend/timezone.py`. Current app-created dry-run business timestamp writes now use MMT helpers; legacy SQLite
`datetime('now')` defaults remain documented fallback behavior and are not destructively rewritten.

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

**Phase 4B complete (2026-06-16):** AccountService (platform identity → one canonical customer, idempotent, gap-safe
code), account-link short codes (hash-only, one-time, 24h, reason-opaque; merge is dry-run/no-mutation),
NotificationService (queue-first; retry/dead-letter; placeholder policy; **no sender**), idempotency helpers +
dry-run payment/provision boundary, and a WAL-safe `sqlite3.Connection.backup()` script (`bin/backup_db.py`).
Additive migration `0002_phase4b.sql`. **48 tests PASS.** No platform sends, no real customers, no live Hiddify
mutations, no services started; de1 stays `status=test`. See PHASE4B_ACCOUNT_NOTIFICATION_BACKUP.md.

**de1 pre-live tuning (2026-06-16) — PARTIAL** ([PHASE4_PRELIVE_DE1_TUNING.md](PHASE4_PRELIVE_DE1_TUNING.md)): firewall
verified (**no change needed** — Hiddify's nf_tables ACCEPTs precede ufw; 22/80/443 tcp + 443 udp + 55573 open, SSH
safe; 8388 loopback-only by design); **SSH password login disabled** (root key-only retained; verified by fresh login
+ refused password attempt; cloud-init's `PasswordAuthentication yes` neutralized so the `99-` drop-in actually wins);
all Hiddify services healthy; host key pinned. **Leaked default-user/server keys → `REBUILD_REQUIRED_BEFORE_LIVE`**
(no safe surgical regen in Hiddify; did not improvise). RAM balloon-risk = accepted. **de1 stays `status=test`.**

**Phase 4C complete (2026-06-16)** ([PHASE4C_DRY_RUN_PROVISIONING.md](PHASE4C_DRY_RUN_PROVISIONING.md)): dry-run
provisioning orchestration wired end-to-end (approve → subscription snapshot → access-profile placeholder → provisioning
plan → delivery enqueue → audit), exactly-once, with a forward-only compensation model. **Live provisioning is
hard-disabled** and refuses even with the env latch + `--live --confirm` (blockers: `phase4c_live_disabled`,
`leaked_key_rebuild_pending`, `node_not_live:test`). Additive migration `0003`. 70 tests PASS. de1 stays `status=test`.

**Phase 5 foundation complete (2026-06-16)** ([PHASE5_TELEGRAM_BOT_FOUNDATION.md](PHASE5_TELEGRAM_BOT_FOUNDATION.md)):
Burmese-primary Telegram bot foundation — dry-run adapter (token redacted; live sends hard-refused), message
catalogue, router (`/start`,`/help`,`/plans`,`/account`,`/link`,`/admin`,fallback), AccountService identity (telegram
id is a platform key, never the customer identity; `/start` idempotent), DB-driven plan rendering, env-driven admin
ids, queue-only NotificationService. **No polling/webhook/Telegram API/send; no service started.** 89 tests PASS.

**Phase 5 transport foundation complete (2026-06-16)** ([PHASE5_TELEGRAM_TRANSPORT_FOUNDATION.md](PHASE5_TELEGRAM_TRANSPORT_FOUNDATION.md)):
gated Bot API transport boundary (token redacted; injectable opener; dry-run default), offset-tracked polling runner
(no daemon), NotificationService sender + outbound worker consuming `outbound_messages` (queued→sent/requeue→backoff/
dead), and a centralized fail-closed double gate (`ALLOW_LIVE_BOT_SENDS`/`ALLOW_LIVE_BOT_POLLING` + `--live-* --confirm`).
107 tests PASS. **No network/send/poll daemon/systemd.**

**Phase 6 delivery foundation complete (2026-06-16)** ([PHASE6_SUBSCRIPTION_DELIVERY_FOUNDATION.md](PHASE6_SUBSCRIPTION_DELIVERY_FOUNDATION.md)):
subscription delivery foundation — `DeliveryPayload` (safe refs only) + branded link rule (`sub.unseen.click/s/<token>`,
assembled in memory, token **hash** stored) + deep-link→copy-link→QR priority (QR **planned**) + mocked Hiddify-output
normalizer + NotificationService/Telegram render integration. Additive migration `0004` (`subscription_deliveries`,
no raw-link column). 122 tests PASS. **No raw links persisted/logged; no network/send.**

**Phase 7 entitlement + node-resilience foundation complete (2026-06-16)** ([PHASE7_ENTITLEMENT_NODE_RESILIENCE.md](PHASE7_ENTITLEMENT_NODE_RESILIENCE.md)):
DB-driven entitlement resolver + node status/health readiness + availability resolver + provisioning-plan integration.
Additive migration `0005`.

**Phase 7 health monitor foundation complete (2026-06-16)** ([PHASE7_HEALTH_MONITOR_FOUNDATION.md](PHASE7_HEALTH_MONITOR_FOUNDATION.md)):
read-only sanitized probes (`node_probe` mock default + opt-in public-TCP) → `metric_writer` (append `node_metrics`) +
`alerting` (idempotent WARN/CRITICAL/DOWN from `settings` thresholds) → feeds `node_resilience` (DOWN→down/dropped;
CRITICAL/WARN→degraded, dry-run candidate but not live-ready). `health_monitor.monitor_once` is single-pass, dry-run by
default; **no daemon/systemd/secrets/network**. 163 tests PASS.

**Phase 8 portal foundation complete (2026-06-16)** ([PHASE8_WEB_PORTAL_FOUNDATION.md](PHASE8_WEB_PORTAL_FOUNDATION.md),
[PORTAL.md](PORTAL.md)): render-only customer portal foundation — app/router boundary returning `PortalResponse`
objects, compact responsive GitHub-inspired neutral UI, DB-driven plans and customer/subscription status, branded
`/s/<opaque-token>` placeholder, and Phase 7 availability rendering. Dry-run tools: `bin/portal_smoke.py`,
`bin/portal_render_dry_run.py`. **No server/public endpoint/auth/live delivery/Hiddify call/Telegram send.** 174 tests
PASS.

**Phase 8A portal preview refinement complete (2026-06-16)** ([PHASE8A_PORTAL_PREVIEW_REFINEMENT.md](PHASE8A_PORTAL_PREVIEW_REFINEMENT.md)):
local preview exporter + UI/copy refinement. Generated sanitized review files under
`/opt/unseen-proxy/tmp/portal-preview/` (git-ignored; not committed), added denser desktop spacing, stacked mobile plan
rows, quick subscription status strip, degraded/unavailable preview state, and stricter safe-output path handling.
**No server/public endpoint/auth/live delivery/Hiddify call/Telegram send.** 179 tests PASS.

**Phase 8B portal auth/session foundation complete (2026-06-16)** ([PHASE8B_PORTAL_AUTH_SESSION_FOUNDATION.md](PHASE8B_PORTAL_AUTH_SESSION_FOUNDATION.md)):
additive migration `0006` adds hash-only `portal_access_tokens` and `portal_sessions`; `portal_tokens`,
`portal_access`, `portal_sessions`, and `branded_link_resolver` provide secure random tokens, hash-only storage,
constant-time verification, expiry/revocation, sanitized audit, dry-run session context, and `/s/<opaque-token>`
resolver behavior. Private pages require `PortalSessionContext`; public pages stay public. **No server/public endpoint/
real cookie service/live delivery/Hiddify call/Telegram send.** Portal token/session timestamps and current app-created
dry-run business timestamps route through MMT helpers. `bin/timezone_audit.py` provides a sanitized local timestamp
check. 198 tests PASS.

**Phase 8C portal HTTP deployment boundary complete (2026-06-16)** ([PHASE8C_PORTAL_HTTP_DEPLOYMENT_BOUNDARY.md](PHASE8C_PORTAL_HTTP_DEPLOYMENT_BOUNDARY.md)):
local-only portal HTTP boundary — `portal_http` (`HttpRequest`/`HttpResponse` + `PortalHttpApp` router wrapping
`render_route` behind a strict route allowlist), `portal_middleware` (hardened security headers + cookie→session
middleware), `portal_cookies` (HttpOnly+Secure+SameSite+Path+Max-Age builder/parser), `portal_csrf` (signed,
constant-time, expiring CSRF foundation), `rate_limit` (in-memory fail-closed fixed-window limiter), `access_log`
(sanitizer redacting `/s/<token>`/cookies/auth headers/query tokens/UUIDs/proxy links/secrets; masks IP), and
`sidecar_boundary` (dry-run `sub.unseen.click`: verifies token hash-backed, safe placeholder, no live Hiddify).
Local-only CLIs: `bin/portal_http_smoke.py`, `bin/sidecar_boundary_smoke.py`, `bin/portal_local_preview_server.py`
(loopback-only; refuses `0.0.0.0`; starts nothing without `--serve-local`; no systemd/nginx/TLS). **No persistent
server/public endpoint/nginx/TLS/systemd/public bind/real cookie service/live subscription resolution/Hiddify/Telegram
network.** CSRF expiry uses MMT helpers; no new DB timestamp writes. 224 tests PASS. de1 stays `status=test`.

**de1 fresh rebuild + clean Hiddify reinstall complete (2026-06-16)** ([PHASE9_DE1_REBUILD_FRESH_HIDDIFY.md](PHASE9_DE1_REBUILD_FRESH_HIDDIFY.md)):
de1 reinstalled fresh (Ubuntu 22.04.5); `known_hosts` refreshed; preflight PASS after Charles's storage upgrade + an
online, approved root-volume grow (`growpart`→`pvresize`→`lvextend`→`resize2fs`) to ~48 GB/40 GB free. Clean
**Hiddify v12.3.3 host reinstall** (pinned `download.sh v12.3.3 --no-gui`, NOT Docker, **umask 022** — no permission
cascade). **API v2 contract re-verified-live** (Hiddify API v2.2.0; auth header; admin base `/<proxy>/api/v2/admin/`;
units **GB**) after a bounded `marshmallow==3.26.1` venv pin (apiflask 3.0.2 had pulled incompatible marshmallow 4.x).
**Disposable-user lifecycle PASS** (create→get→all-configs→patch→delete→404). FAST1/Hysteria2 + FAST2/Shadowsocks +
Secure/VLESS-Reality inbounds present. SSH re-hardened (password-auth off, key-only, port unchanged; verified).
Firewall: 22/80/443 tcp + 443 udp allowed, SSH safe. **`leaked_key_rebuild_pending` CLEARED** (`config` flag False;
seed blocker swapped to `realdevice_protocol_test_pending`). **de1 stays `status=test`; live still hard-disabled by
`phase4c_live_disabled`.** Admin link stored only at `/root/hiddify-de1-admin.link` (0600); no secrets committed.
225 tests PASS.

**Reusable node install runbook (2026-06-16)** ([HIDDIFY_NODE_INSTALL_RUNBOOK.md](HIDDIFY_NODE_INSTALL_RUNBOOK.md)):
the de1 success pattern is now the **baseline install method for all future Hiddify nodes (US, SG1, SG2, …)** —
dedicated VPS (never Master co-location), Ubuntu 22.04 host install (never Docker), version-pinned under **umask 022**,
disk/LVM grown first, admin link `0600` outside git, API verified (bounded `marshmallow==3.26.1` pin if the v4 issue
appears), disposable-user lifecycle, protocols present, SSH hardened, firewall verified, `status=test` until
Charles-gated promotion. Future US/SG installs **must** follow this runbook and must **not** repeat Master co-location
or Docker-on-Master.

**Next: Charles records the real-device FAST1/FAST2/Secure connect PASS** (clears `realdevice_protocol_test_pending`;
`#TASK_for_Charles` in PHASE9_DE1_REBUILD_FRESH_HIDDIFY.md). Then separately-gated tasks remain (public portal
deployment: nginx/TLS + systemd + public-bind approval for the portal HTTP adapter & `sub.unseen.click` sidecar;
periodic monitor + read-only SSH metrics; bot live latches + real opener; Phase 4C live-provisioning flip; set
`node-de.unseen.click` panel domain + cert; RAM lock). **de1 `status=test → live` promotion stays Charles-gated.**

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

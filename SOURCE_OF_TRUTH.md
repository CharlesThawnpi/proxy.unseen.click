# UNSEEN PROXY — SOURCE OF TRUTH (consolidated, auto-generated)

> **Generated:** 2026-06-16T17:53:58Z — by `scripts/build_source_of_truth.sh`.
> **This is the live project state for external readers (e.g. the Custom GPT).** It is DERIVED from the
> canonical docs below and regenerated each task. Upload THIS file to the GPT (not IMPLEMENTATION_PLAN.md,
> which is the static v1.9 plan). Re-download after updates.

## How the canonical docs relate
- `IMPLEMENTATION_PLAN.md` — static v1.9 **plan/intent** (not updated as work proceeds).
- `docs/DECISIONS.md` — **ADRs that SUPERSEDE the plan** where they differ (authoritative).
- `docs/CURRENT_STATUS.md` — **live phase tracker + next task**.
- `docs/TIMEZONE_POLICY.md` — **project-wide business/customer timezone rule**.
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
- **Business/customer dates use Myanmar Time:** MMT, UTC+06:30, `Asia/Yangon`; external UTC converts at the boundary.


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
| 3 | Hiddify API & subscription compatibility audit | **DONE (PASS) — Hiddify v12.3.3 on de1; API v2 contract VERIFIED-LIVE; disposable test user create→sub→delete confirmed.** Phase 4 API layer UNBLOCKED. **Re-verified after a fresh de1 rebuild + clean reinstall (2026-06-16, PHASE9_DE1_REBUILD_FRESH_HIDDIFY.md): contract re-confirmed (bounded `marshmallow==3.26.1` venv pin needed), disposable-user lifecycle PASS, FAST1/FAST2/Secure present, SSH hardened. `leaked_key_rebuild_pending` CLEARED.** **Node domain `node-de.unseen.click` now SET with a valid Let's Encrypt cert (2026-06-16): added via `hiddifypanel add-domain` + `apply_configs.sh`; API/all-configs verified-live over the public node-de path with valid TLS; subscription output now references `node-de.unseen.click` (resolves Phase 9 blocker #4).** **Real-device import (2026-06-16): two issues found+addressed. (1) Mobile `127.0.0.1:64127` = app-side core (server output clean). (2) Windows `[SingboxParser] ... outbounds[37].tunnel-per-resolver: json: unknown field` = generator↔parser mismatch from the DNSTT outbound — FIXED by disabling DNSTT (`set-setting dnstt_enable=false` + apply; DNSTT is not FAST1/FAST2/Secure). After-render confirms `tunnel-per-resolver`=0/dnstt=0; FAST1/Secure outbounds intact. Disposable user recreated DNSTT-free. Secondary (deferred): sub output still multi-domain (raw-IP/sslip won't connect; manual panel prune). Real-device retest can proceed once Charles re-imports the fresh node-de subscription on an updated app. (3) Hiddify's default profile was too broad (100 outbounds across raw-IP/sslip, no clean FAST1/FAST2/Secure) — PRUNED to a clean UNSEEN-only profile via supported `set-setting` + `sub_link_only`: now exactly hysteria2(FAST1)+shadowsocks(FAST2)+vless-Reality(Secure), all on node-de (FAST1 udp:14430, FAST2 :16753, Secure tcp:443+decoy SNI), no raw-IP/sslip/vmess/tuic/naive/mieru/ssh/wireguard, no tunnel-per-resolver/dnstt/private-keys (100→9 outbounds). Disposable user rotated (Charles pasted profile text). Protocols NOT yet PASS — awaits real-device connect.** **Real-device diagnosis (2026-06-16): PARTIAL — import succeeds on iOS; node is server-side READY + externally reachable for all three (DNS/TLS verify=0; TCP 443/16753/80/22 OPEN; UDP 14430/443 open|filtered; explicit fw ACCEPT 14430/udp; SS 16753 reachable via default INPUT=ACCEPT — Phase 10 must add an explicit 16753 allow; Reality 443→internal 19411, decoy SNI i.pinimg.com; panel API re-verified 200, marshmallow 3.26.1). But real-device per-protocol CONNECT is unconfirmed: iOS SS Speedtest upload drops, Windows VPN-mode "failed to start background core" (client-side), Facebook unreliable. Decision = HOLD (no node tuning; buffers already 64MB, no server errors). `realdevice_protocol_test_pending` REMAINS.** Remaining: real-device FAST1/FAST2/Secure connect PASS + RAM lock. See HIDDIFY_API_CONTRACT.md + PHASE3_DE1_HIDDIFY_LIVE_VERIFY.md + PHASE9_DE1_REBUILD_FRESH_HIDDIFY.md |
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

**de1 real-device protocol diagnosis (2026-06-16) — PARTIAL** ([PHASE9_DE1_REBUILD_FRESH_HIDDIFY.md](PHASE9_DE1_REBUILD_FRESH_HIDDIFY.md)
addendum): after the clean import, the node is **server-side READY + externally reachable for all three protocols** —
sanitized render still clean (7 outbounds: hy2+ss+vless-Reality + 2 client selector groups "lowest"/"balance"/auto +
2 direct; 0 raw-IP/sslip/dnstt/nonReality/private-keys; all → node-de), all `hiddify-*` active, **panel API re-verified
200** (marshmallow 3.26.1 pin intact; `openapi.json` 500 is cosmetic), DNS/TLS verify=0, TCP 443/16753/80/22 OPEN, UDP
14430/443 open|filtered, explicit fw ACCEPT for 14430/udp, Reality 443→internal 19411 with decoy SNI `i.pinimg.com`.
**But real-device per-protocol CONNECT is unconfirmed:** iOS SS Speedtest **upload drops**, **Facebook unreliable**,
**Windows VPN-mode "failed to start background core" = client-side** (TUN/Wintun/Administrator/app-version); Windows
**Proxy mode is not full-VPN proof**. **Decision = HOLD (no node tuning** — UDP buffers already 64 MB, no server errors).
The "lowest"/"balance" selectors are **sing-box client groups, not protocols and not UNSEEN's final labels** (backend/
portal handles UNSEEN naming). **`realdevice_protocol_test_pending` REMAINS; de1 stays `status=test`; no node change made.**
Phase-10 hardening note: when tightening INPUT to DROP, **add an explicit allow for SS 16753** (today reachable only via
default `INPUT=ACCEPT`).

**de1 mobile import PASS + Hiddify label/selector finding (2026-06-16) — Decision C** ([PHASE9_DE1_REBUILD_FRESH_HIDDIFY.md](PHASE9_DE1_REBUILD_FRESH_HIDDIFY.md)
addendum): after Charles deleted + reinstalled the Hiddify App, **mobile import now PASS** (Windows too); the earlier iOS
"connection refused" was an **app/cache/install-state** issue, not a node fault. On the naming/selector cleanup ask: there
is **no safe supported way** to rename the protocol entries to FAST1/FAST2/Secure or to hide the selector groups on the
node. The outbound **tag** is built in `singbox.py:to_singbox` from the auto-generated `proxy.name` (no per-proxy
display-name setting; `ConfigEnum` has only `branding_*`); the **"Select"+"Auto"** groups are **hardcoded** in
`singbox.py:configs_as_json` and referenced by the template (`final:"Select"`, dns detour) so removing them breaks the
profile; both would require venv source/DB edits that **Hiddify regenerates on upgrade**. **"lowest"/"balance" are not in
de1's output at all** — they are **Hiddify App client-side UI groups** (the node emits only Select/Auto; "load-balance"
is Clash-template-only). **Decision = C: keep the clean profile unchanged; UNSEEN labels (FAST1=Hysteria2,
FAST2=Shadowsocks, Secure=VLESS-Reality) are presented by bot/portal/delivery** (a backend-generated custom profile is the
path if ever required). **No node change made; de1 stays `status=test`; `realdevice_protocol_test_pending` remains.**

**de1 FAST1/Hysteria2 timeout diagnosis (2026-06-16) — server EXONERATED; likely mobile-network UDP (Decision C, HOLD)**
([PHASE9_DE1_REBUILD_FRESH_HIDDIFY.md](PHASE9_DE1_REBUILD_FRESH_HIDDIFY.md) addendum): Charles's **FAST1/Hysteria2 times
out on connect** (a protocol-level failure, not import). Server side is **fully correct and exonerated**: hiddify-core
listens on **udp/14430** (one Hy2 inbound per domain: 14427/14428/14430), **explicit firewall ACCEPT** for those udp
ports, and an on-node boolean comparison confirms the client targets node-de's `hysteria_in_14430` with **matching port +
salamander obfs-password + user auth + sni** (no secrets printed); singbox active with **0 hysteria/quic/auth/obfs/
handshake errors**. From the Master (clean network): DNS ✓, TCP 443/16753 OPEN, UDP 14430 **open|filtered** (not refused).
Control FAST2(SS 16753 tcp+udp)/Secure(Reality 443) listeners healthy → **only the UDP/Hysteria2 path is affected**.
**Likely cause = C (mobile-carrier UDP/QUIC throttling on the high port)** — a *timeout* on QUIC/UDP while TCP works is the
classic signature; salamander obfs is already enabled (best DPI evasion) and **no supported port-hop toggle exists**, so
**no safe server change applies → HOLD, no node change.** **`realdevice_protocol_test_pending` remains** (Hysteria2 not
PASS; FAST2/Secure still need separate tests). Hysteria2 is UDP-based: fast but **network-dependent**.

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


---

# TIMEZONE POLICY (docs/TIMEZONE_POLICY.md)

# TIMEZONE POLICY

> **Decision date:** 2026-06-16 MMT
> **Status:** ACCEPTED — project-wide business/customer time rule.

## Myanmar Time Rule

All project, system, and product business dates/times use **Myanmar Time**.

- **Project timezone:** Myanmar Time
- **Abbreviation:** MMT
- **Offset:** UTC+06:30
- **IANA timezone:** `Asia/Yangon`

## Business / Customer Dates

Customer-visible dates and times must be shown in MMT. This includes portal, bot, support, admin, reports, and status
surfaces unless the value is explicitly a technical/external UTC timestamp.

## Subscription Lifecycle

Subscription start/end dates use MMT.

Example:

- Start: `2026-06-16 09:00:00 MMT`
- End for a 30-day Plan: `2026-07-16 09:00:00 MMT`

If a node/API expects a different timezone or UTC-derived value later, convert at the integration boundary and keep the
business source value in MMT.

## Payments / Invoices

Payment/order approval timestamps, invoice dates, and receipt dates use MMT. Financial documents remain English, but
their dates are Myanmar Time dates.

## Bot / Portal / Admin Displays

Telegram bot copy, customer portal pages, future admin pages, support summaries, and report examples must label or
otherwise clearly imply MMT for customer/business dates.

## External UTC Conversion Rule

If an external API returns UTC, convert it to MMT before customer/business use. Do not store or display an external UTC
timestamp as a subscription/payment/customer-facing date without conversion.

## Technical Log Exception

Technical logs may use UTC later when that is operationally useful, but those fields must be explicitly labeled as UTC
and must not be confused with business dates. Customer-facing and product lifecycle dates remain MMT.

## Implementation Helpers

`backend/timezone.py` provides:

- `now_mmt()`
- `to_mmt(dt)`
- `format_mmt(dt)`
- `today_mmt()`
- `parse_mmt(value)`
- `storage_mmt(dt)`

New code should use timezone-aware datetimes and reject/avoid naive datetimes.

## Current App-Write Coverage

As of the Phase 8B MMT timestamp foundation, current app-created dry-run business writes route through
`backend.timezone` helpers instead of SQLite clock fallbacks for:

- Subscription `start_date` / `expiry_date`.
- Payment-order `approved_at`.
- Outbound-message `created_at`, `sent_at`, and `next_attempt_at`.
- Audit-log `created_at`.
- Idempotency-key `created_at` / `updated_at`.
- Account-link token `expires_at` / `consumed_at`.
- Node-alert `raised_at` / `cleared_at`.
- Portal access-token/session `created_at`, `expires_at`, `last_verified_at`, and `revoked_at`.

Legacy SQLite `datetime('now')` defaults remain in historical migrations as documented fallbacks only; they should not
be the primary app-created business timestamp path.

## Known Follow-Ups Before Live Launch

- Keep auditing legacy SQLite defaults and technical timestamp paths; do not destructively rewrite historical
  migrations.
- Review backup, health-monitor, and other purely technical timestamp paths and explicitly label or convert them before
  they reach customer/business surfaces.
- Review invoices/receipts before launch so every generated financial date is MMT.
- Review bot/portal/admin display paths and add explicit MMT labels wherever ambiguity remains.
- Decide whether purely technical logs should remain UTC; if so, label them clearly as UTC.


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

## ADR-004 — Myanmar Time is the project business timezone

- **Date:** 2026-06-16 MMT
- **Status:** ACCEPTED (Charles)
- **Supersedes/refines:** Any prior assumption that customer/product/business dates are UTC by default.

### Decision

All UNSEEN PROXY business, customer, product, and report dates/times use **Myanmar Time**:

- Abbreviation: **MMT**
- Offset: **UTC+06:30**
- IANA timezone: **`Asia/Yangon`**

Customer-visible dates, subscription start/end dates, payment/order approval timestamps, invoice/receipt dates, bot
messages, portal pages, admin displays, and business reports must use MMT. External UTC timestamps must be converted to
MMT at the boundary before customer/business use.

### Technical exception

Technical logs may use UTC later only when explicitly labeled as UTC. UTC log fields must not be used as ambiguous
business dates.

### Implementation

`backend/timezone.py` is the central helper module for MMT conversion/formatting. Existing SQLite schema defaults using
`datetime('now')` are documented as legacy pre-live behavior. Current app-created dry-run business timestamps for
subscriptions, payment approvals, outbound messages, audit/idempotency rows, and portal token/session rows are routed
through the MMT helper rather than relying on SQLite defaults; account-link token and node-alert service writes also set
MMT timestamps explicitly.


---

# VERIFIED HIDDIFY API CONTRACT (head of docs/HIDDIFY_API_CONTRACT.md)

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
> ### ✅ Re-verified after the 2026-06-16 real-device diagnosis (post-restart)
> A controlled node restart cluster occurred (~19:19; Charles re-applied SSH/DNS) — the contract was **re-confirmed
> still live afterward**: over `node-de.unseen.click`, `GET /api/v2/admin/me/` → **200**, `/admin/user/` → **200**,
> `/admin/server_status/` → **200**; no-key `me/` → **403** (route + auth enforced). **marshmallow still pinned 3.26.1.**
> **Caveat (cosmetic):** `GET /api/v2/openapi.json` over HTTP now returns **500** under the downgraded marshmallow —
> apiflask's OpenAPI *spec-document generation* fails, but this is **doc/UI only**; the functional admin CRUD endpoints
> the orchestrator depends on return 200, so the contract is unaffected. (This reconciles the earlier "spec builds fine
> in-process" note: that predates the marshmallow-4→3.26.1 downgrade now in effect.) **All status codes only — no
> bodies/links/UUIDs/keys printed; admin link used internally on-node.**
> ### 🏷️ Generated sing-box output naming/groups (2026-06-16) — not API-configurable
> The client sing-box profile's **outbound tags and selector groups are not controllable via the API or any
> `hiddifypanel` setting.** Outbound tags come from `singbox.py:to_singbox` (`{extra_info} {proxy.name} § {port}
> {dbdomain.id}`; `proxy.name` is auto-generated and `apply_configs`-regenerated); the **"Select"** (selector) +
> **"Auto"** (urltest) groups are **hardcoded** in `singbox.py:configs_as_json`. `ConfigEnum` exposes only
> `branding_title`/`branding_site`/`branding_freetext` (panel branding). UNSEEN customer labels (FAST1/FAST2/Secure) are
> therefore an **UNSEEN delivery-layer concern** (bot/portal, or a backend-generated profile), **not** a Hiddify API
> option. "lowest"/"balance" seen in-app are **client-side** Hiddify-App groups, never emitted by the node.
> ### 🛰️ Per-domain protocol inbounds (2026-06-16)
> Hiddify generates **one inbound per protocol per configured domain**. With node-de + raw-IP + sslip configured, the
> node runs **three Hysteria2 inbounds** (`hysteria_in_14427/14428/14430` = raw-IP/sslip/node-de) on distinct UDP ports;
> the **customer profile (node-de) uses udp/14430**. The raw-IP/sslip inbounds belong to the `sub_link_only` domains
> (excluded from customer subs). An on-node boolean compare confirmed the generated client outbound's **port + salamander
> obfs-password + user auth + sni match** the node-de inbound — i.e. the generated profile is consistent with the server
> config. (Implication for the orchestrator: protocol port numbers are **per-node/per-domain and dynamic** — always read
> them from the generated profile, never hardcode.)
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


---

# RECENT CHANGELOG (head of docs/CHANGELOG.md)

# CHANGELOG

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §32, §34
> **Status:** Phase 1 skeleton — running log of changes by date

Chronological record of notable changes to the UNSEEN PROXY project.

## 2026-06-16 — de1: diagnose FAST1/Hysteria2 timeout — server-side EXONERATED; likely mobile-network UDP (Decision C, HOLD)

- **Symptom:** mobile/Windows **import PASS**, but **FAST1/Hysteria2 times out on connect** for Charles. This is a
  **protocol-level connectivity** failure, **not** an import/profile-shape failure. (Labels unchanged: FAST1=Hysteria2,
  FAST2=Shadowsocks, Secure=VLESS-Reality.)
- **Profile re-scan (sanitized; counts/booleans/port only):** still clean — 1 disposable user; **7 outbounds**
  (hysteria2×1 + shadowsocks×1 + vless-Reality×1 + Select/Auto groups + 2 direct); raw-IP=0, sslip=0, dnstt=0,
  tunnel-per-resolver=0, private-key=0, vmess/tuic/naive/wireguard=0. **Hysteria2 outbound:** server=node-de, **port
  14430**, salamander **obfs present (+password)**, auth password present, TLS enabled (insecure=true, sni=node-de, alpn).
- **Server-side EXONERATED (causes A + B ruled out):**
  - **Listener/firewall (A):** hiddify-core listens on **udp/14430** (and 14427/14428 — one Hy2 inbound **per configured
    domain**: raw-IP/sslip/node-de); **explicit iptables ACCEPT for 14430/14428/14427 udp**; INPUT policy ACCEPT.
  - **Profile↔server match (B):** the client targets node-de's inbound `hysteria_in_14430` — **port match ✓, salamander
    obfs-password match ✓, user auth-password present ✓, TLS sni=node-de ✓** (verified by an on-node boolean comparison;
    **no secret values printed**).
  - **Health/logs:** hiddify-singbox active (no restart in the test window); **0 logged hysteria/quic/auth/obfs/handshake
    errors** in the last 2h; resources fine (load ~0.15, ~2.9 GiB free, disk 17%). `UdpRcvbufErrors≈380/180240` (~0.2%) =
    negligible background, not a connection-killer.
- **External reachability (Master, no payloads):** DNS node-de → 5.249.160.59 ✓; TCP control **443/16753 OPEN** ✓; UDP
  **14430/14428/14427 open|filtered** (not refused) from a clean datacenter network ✓. (Honest limitation: UDP
  *delivery* can't be definitively proven without a Hysteria2 handshake payload, which was intentionally **not** sent.)
- **Control (FAST2/Secure, not tuned):** SS **16753 tcp+udp** listening; Reality **443** listening; xray/haproxy active;
  **0 reality handshake errors** → only the **UDP/Hysteria2** path is in question; TCP-based protocols are up.
- **Likely cause = C (mobile-network UDP/Hysteria2 instability).** Server is correct + reachable from a clean network;
  the failure is a **timeout** (not refusal, not auth/obfs error) on a **QUIC/UDP** protocol on a high port (14430) while
  TCP-based import/SS/Reality work — the classic signature of **mobile-carrier UDP/QUIC throttling/blocking** (common on
  Myanmar mobile data). **D (client app) secondary** — rule out via a Wi-Fi-vs-mobile-data retest.
- **Tuning decision = HOLD (no node change).** Supported Hiddify Hy2 knobs are already sensibly set
  (`hysteria_enable=true`, `hysteria_obfs_enable=true` → salamander already on = best DPI evasion, `hysteria_port`,
  `hysteria_up/down_mbps`=150/300). **No supported port-hop toggle exists** (per-domain inbounds, not a hop range). No
  safe/supported server change would fix a carrier-side UDP block → nothing applied.
- **No node change made.** de1 stays **`status=test`**; **`realdevice_protocol_test_pending` remains** (Hysteria2 not
  PASS; FAST2/Secure still need separate tests). **Secret-safety:** only counts/booleans/ports/HTTP-status emitted;
  server↔client comparison done on-node and reported as booleans (no obfs/auth/keys/UUIDs printed); temp scanners
  removed; logs redacted. Docs + SOURCE_OF_TRUTH regenerated.

## 2026-06-16 — de1: mobile import PASS after app reinstall; Hiddify selector/label control findings — Decision C (no safe node-side rename/hide)

- **Mobile import now PASS.** Charles deleted + reinstalled the Hiddify App on mobile → **import works** (Windows
  import also works; the clean de1 profile is importable). The earlier iOS "connection refused" / import failure was an
  **app/cache/install-state** condition, **not** a node/profile fault (server output was already verified import-clean).
  Remaining open items are now **(a) naming/selector cleanliness** (this entry) and **(b) real per-protocol
  connectivity PASS** (still pending).
- **Profile re-scan (sanitized app-context sing-box render; counts/booleans only, temp shredded):** unchanged & clean —
  **7 outbounds** = hysteria2×1 + shadowsocks×1 + vless-Reality×1 + **2 groups** (`selector` tag **"Select"**, 4 members;
  `urltest` tag **"Auto"**, 3 members) + 2 `direct`. `vless_nonreality=0`, raw-IP=0, sslip=0, dnstt=0,
  tunnel-per-resolver=0, private-key=0, vmess/tuic/naive/wireguard=0. Import-clean retained.
- **"lowest"/"balance" explained — they are NOT in de1's output.** The node's sing-box profile emits only **"Select"**
  (selector) + **"Auto"** (urltest); "load-balance" exists **only in the Clash templates** (`clash_config*.yml`), which
  the Hiddify App (sing-box core) does not use. So **"lowest" and "balance" are Hiddify App (HiddifyNext) client-side UI
  groups**, generated by the app after import — **not UNSEEN protocols and not node-controllable.**
- **Label/group control finding — Decision C (no safe supported method):**
  - **Rename Hysteria2→FAST1 / Shadowsocks→FAST2 / VLESS-Reality→Secure:** NOT possible via any supported
    `hiddifypanel` setting / DB flag / API option. The outbound **tag** is built in
    `hutils/proxy/singbox.py:to_singbox` as `f"{extra_info} {name} § {port} {dbdomain.id}"`, where `name = proxy.name`
    is an **auto-generated Proxy DB field** (regenerated on `apply_configs`). No per-proxy custom-display-name setting
    exists. `ConfigEnum` exposes only `branding_title`/`branding_site`/`branding_freetext` (panel/profile branding) —
    nothing for outbound tags.
  - **Hide/remove "Select"/"Auto" groups:** **hardcoded** in `singbox.py:configs_as_json` (not settings-driven), and the
    template references `"final": "Select"` + dns `detour: "Select"` — removing them **breaks** the profile. Source-edit
    only, **not upgrade-durable**.
  - Achieving the labels would require **patching venv source** (`singbox.py`/`shared.py`) or DB rows that Hiddify
    regenerates — which **breaks on every Hiddify upgrade/reinstall** and risks the clean profile. **Not done.**
- **Decision = C.** Keep the current clean profile **unchanged**; present **UNSEEN labels (FAST1=Hysteria2,
  FAST2=Shadowsocks, Secure=VLESS-Reality) in the bot/portal/customer instructions/delivery layer.** If a fully
  custom-labeled client profile is ever required, the **UNSEEN backend should generate/sanitize the customer sing-box
  profile itself** (the delivery/link layer already mediates output) — never hand-patch Hiddify templates.
- **No node change made** (no `set-setting`, no template edit, no service restart, no disposable-user recreate — output
  unchanged). de1 stays **`status=test`**; **`realdevice_protocol_test_pending` remains** (awaits Charles's actual
  per-protocol connectivity PASS). **Secret-safety:** only counts/booleans/tags(safe-filtered) emitted; admin link used
  internally on-node; temp scanner removed; no secrets printed/committed. Docs + SOURCE_OF_TRUTH regenerated.

## 2026-06-16 — de1: diagnose real-device protocol connectivity after clean import — PARTIAL (server-side READY; client connect unconfirmed)

- **Why:** Charles's fresh pruned import now **succeeds on iOS** (profile shows two auto selectors "lowest"/"balance"
  + VLESS-Reality + Shadowsocks + Hysteria2 entries). But: iOS Shadowsocks connects yet **Speedtest upload often
  fails/drops**; **Facebook still not reliably loaded**; **Windows VPN mode fails** with "Unexpected failure failed to
  start background core" (Windows Proxy mode connects but is **not** full-device VPN proof). This task diagnoses
  node-side protocol/client-routing readiness — **not** treated as PASS.
- **Clean output re-verified (sanitized app-context sing-box render; counts only, no links/UUIDs/keys):** **1**
  `disposable-test-realdevice` user (the only customer-type user; 2 non-customer install users `default`/`Test` also
  present — not real customers). **7 outbounds (3.7 KB):** hysteria2×1 (FAST1) + shadowsocks×1 (FAST2) + vless-Reality×1
  (Secure) + **2 client selector groups** (1 `selector` + 1 `urltest`) + 2 `direct`. `vless_nonreality=0`, raw-IP=0,


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
[PHASE2_3_DE_NODE_PLAN.md](PHASE2_3_DE_NODE_PLAN.md). Node domain `node-de.unseen.click` — **now set as a Hiddify
`direct` domain with a valid Let's Encrypt cert (2026-06-16); API + subscription verified-live over the public node-de
path with valid TLS** (the install had defaulted to raw-IP/sslip.io, which broke real-device import). de1 stays
`status=test`. See [HIDDIFY_NODE_INSTALL_RUNBOOK.md](HIDDIFY_NODE_INSTALL_RUNBOOK.md) §5A + PHASE9 addendum.

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


---

_End of consolidated source of truth. Regenerate with \`bash scripts/build_source_of_truth.sh\`._

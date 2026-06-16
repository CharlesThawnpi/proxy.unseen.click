# CHANGELOG

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §32, §34
> **Status:** Phase 1 skeleton — running log of changes by date

Chronological record of notable changes to the UNSEEN PROXY project.

## 2026-06-16 — Phase 6: subscription delivery foundation (dry-run) — PASS

- **Dry-run only** (stdlib): no live Hiddify call, no real subscription fetch from de1, no Telegram send, and **no raw
  subscription/proxy link or QR payload persisted/logged**. de1 stays `status=test`. See
  [PHASE6_SUBSCRIPTION_DELIVERY_FOUNDATION.md](PHASE6_SUBSCRIPTION_DELIVERY_FOUNDATION.md).
- **Additive migration** `0004_phase6.sql`: new `subscription_deliveries` (safe refs/flags + branded token **hash**
  only; **no raw-link/QR column** by design). Idempotent re-run verified.
- **`link_renderer`** — branded link `https://sub.unseen.click/s/<token>` assembled in memory only; token **hash**
  stored; raw-proxy-link detection (`hiddify://`/`vless://`/`ss://`/`hy2://`/`/api/v2/`/`all-configs`) + redaction.
- **`hiddify_subscription_output`** — normalizes a **mocked** output to a sanitized summary (counts + engine names +
  booleans); raw output discarded, never logged. **`qr_renderer`** — QR honestly **planned**, not generated (stdlib;
  no risky dep). **`delivery_payloads`/`subscription_delivery`** — `DeliveryPayload` (refs/flags only; mode priority
  deep-link → copy-link → QR); `prepare_delivery` persists safe refs + audit + enqueues a notification (`payload_ref`
  only); `_guard_no_raw_link` refuses to persist/log raw links.
- `telegram_messages.delivery_preview` — safe Burmese-primary preview (no link/token/QR). New CLIs:
  `bin/subscription_delivery_smoke.py`, `bin/render_delivery_dry_run.py` (temp DB / mocked output).
- **Tests: 122 PASS** (107 + 15 new, incl. no-network-call guard + no-raw-link-in-DB/audit). Updated
  DATABASE/BOT_FLOWS/SECURITY/DEPLOYMENT/CURRENT_STATUS; new PHASE6 doc.

## 2026-06-16 — Phase 5: gated Telegram transport foundation (dry-run) — PASS

- **Dry-run only, gated** (stdlib): no Telegram API call, no send, no polling daemon, no webhook, no systemd service;
  de1 stays `status=test`. See [PHASE5_TELEGRAM_TRANSPORT_FOUNDATION.md](PHASE5_TELEGRAM_TRANSPORT_FOUNDATION.md).
- **`telegram_transport`** — Bot API boundary (`getUpdates`/`sendMessage`/`editMessageText`/`answerCallbackQuery`);
  injectable `opener` (tests mock; no real network); dry-run default; token name-mangled + redacted; the token-bearing
  URL is never logged/returned; timeout/retry boundaries.
- **`telegram_polling`** — offset-tracked runner routing batches through `TelegramRouter`; no daemon; live poll
  hard-refused without the gate. **`notification_sender`/`outbound_worker`** — consume queued telegram
  `outbound_messages`, render from `payload_ref` (template key only), transitions queued→sent / queued (attempts++,
  backoff) / dead; live send hard-refused without the gate.
- **`runtime_gates`** — centralized fail-closed double gate: live send needs `ALLOW_LIVE_BOT_SENDS=1` + `--live-send
  --confirm`; live poll needs `ALLOW_LIVE_BOT_POLLING=1` + `--live-poll --confirm`. Even when gated, tests use a mock
  transport.
- `.env.example`: added `ALLOW_LIVE_BOT_SENDS=0` / `ALLOW_LIVE_BOT_POLLING=0`. New CLIs:
  `bin/telegram_poll_dry_run.py`, `bin/outbound_worker_dry_run.py`, `bin/send_notification_dry_run.py` (temp DB/mock).
  **Tests: 107 PASS** (89 + 18 new, incl. no-network-call guard). Updated BOT_FLOWS/SECURITY/DEPLOYMENT/CURRENT_STATUS;
  new transport doc. No schema change.

## 2026-06-16 — Phase 5: Telegram bot foundation (Burmese-primary, dry-run) — PASS

- **Dry-run only** (stdlib): no Telegram API call, no message sent, no polling/webhook, no service started, no live
  provisioning; de1 stays `status=test`. See [PHASE5_TELEGRAM_BOT_FOUNDATION.md](PHASE5_TELEGRAM_BOT_FOUNDATION.md).
- **New modules:** `telegram_adapter` (dry-run boundary; token redacted; live sends hard-refused via
  `config.PHASE5_LIVE_SEND_DISABLED`), `telegram_messages` (Burmese-primary catalogue; English product terms kept),
  `telegram_commands` (defensive `parse_update`), `bot_flows` (DB-driven plan/status/admin content), `telegram_router`
  (routes `/start`,`/help`,`/plans`,`/account`,`/link`,`/admin`,fallback), `bot_context` (env-driven admin ids).
- **Identity:** `/start` resolves via AccountService (telegram platform); the Telegram id is a `platform_accounts`
  key, never the customer identity; `/start` idempotent. **Plans render from DB rows** (DE default, SG premium-only
  PRO/MAX, FAST label rule) — not hardcoded.
- **Admin:** ids from `ADMIN_TELEGRAM_IDS` (fallback `TELEGRAM_ADMIN_IDS`), parsed safely, never logged; `/admin` =
  DB-only sanitized counts for admins, Burmese denial otherwise. **NotificationService** integration is queue-only
  (`payload_ref`, no body/secret).
- `.env.example`: added `ADMIN_TELEGRAM_IDS` placeholder (kept `TELEGRAM_ADMIN_IDS` alias); no real token/id committed.
- New CLIs: `bin/telegram_bot_smoke.py`, `bin/render_telegram_messages.py` (temp DB). **Tests: 89 PASS** (70 + 19 new,
  incl. no-network-call guard + token-redaction). Updated BOT_FLOWS/SECURITY/DEPLOYMENT/CURRENT_STATUS; new PHASE5 doc.

## 2026-06-16 — Phase 4C: dry-run provisioning orchestration — PASS

- **Dry-run orchestration only** (stdlib). No live Hiddify call, no Hiddify user, no real customer/subscription, no
  message sent, no service started; de1 stays `status=test`; live hard-disabled. See
  [PHASE4C_DRY_RUN_PROVISIONING.md](PHASE4C_DRY_RUN_PROVISIONING.md).
- **Additive migration** `0003_phase4c.sql`: `subscriptions.provision_status`, `payment_orders.approved_at`, new
  `provisioning_attempts` (FK-enforced) + indexes. Idempotent re-run verified.
- **Flow wired:** AccountService → `payment_approval_service` (idempotent dry-run approval) → `subscription_service`
  (order-time snapshots, deterministic dates) → `access_profile_service` (placeholder hash; no raw token/URL/UUID) →
  `provisioning_plan` (entitlements from DB rows + candidate nodes + live blockers + sanitized Hiddify mutation intent,
  GiB→GB) → `provisioning_service` (dry-run; **live hard-refused**) → NotificationService (delivery enqueue,
  `payload_ref` only) → `audit` (sanitized) with a forward-only `compensation` model.
- **Exactly-once** across `payment_approval`/`provision_subscription` scopes: duplicate flow creates no duplicate
  subscription/notification/attempt. **Live refuses even with env latch + `--live --confirm`** (blockers:
  `phase4c_live_disabled`, `leaked_key_rebuild_pending`, `node_not_live:test`).
- New CLIs: `bin/approve_payment_dry_run.py`, `bin/provision_subscription_dry_run.py`,
  `bin/provisioning_flow_smoke.py`. **Tests: 70 PASS** (48 + 22 new; incl. a no-network-call guard). Updated
  DATABASE/CURRENT_STATUS + REGIONS/PROTOCOLS/NODES/SECURITY/DEPLOYMENT notes; new PHASE4C doc.

## 2026-06-16 — Phase 4: de1 pre-live tuning & security hardening (test-safe) — PARTIAL

- **No customers/subscriptions/live provisioning; de1 stays `status=test`.** See
  [PHASE4_PRELIVE_DE1_TUNING.md](PHASE4_PRELIVE_DE1_TUNING.md).
- **Firewall — no change required.** ufw + Hiddify share one nf_tables ruleset; Hiddify's `ACCEPT` rules precede
  ufw's chains in `INPUT`, so required ports (22/80/443 tcp, 443 udp, 55573, dynamic Hiddify inbounds) are open while
  ufw default-denies the rest. Verified from the Master: 22/80/443 tcp OPEN (443 TLS→200), 55573 OPEN; **8388 filtered
  by design** (`ss-server` is loopback-only; Shadowsocks fronts via 443/faketls). SSH allowed throughout.
- **SSH hardened — PASS.** Found `50-cloud-init.conf` set `PasswordAuthentication yes`; since sshd uses the first
  keyword value, a `99-` drop-in alone would lose — so neutralized the cloud-init line (backed up on node) + added
  `/etc/cloud/cloud.cfg.d/99-unseen-ssh.cfg` (`ssh_pwauth: false`) + created
  `/etc/ssh/sshd_config.d/99-unseen-proxy-hardening.conf` (`PasswordAuthentication no`, `KbdInteractiveAuthentication
  no`, `PubkeyAuthentication yes`). Root key login kept. Validated with `sshd -t`/`sshd -T` and a held-open
  ControlMaster revert path; graceful `reload`; fresh key login verified; password-only attempt **refused**.
- **Leaked-key handling — `REBUILD_REQUIRED_BEFORE_LIVE`.** No Hiddify-supported safe surgical regen of the leaked
  default-user/server keys exists (`reset-owner-password` = admin password only; reinstall = destructive). Did not
  improvise. Dry-run work may continue on the test node; first live/real provisioning is blocked until rebuild.
- **Host key pinned** in the Master `known_hosts` (`ED25519 SHA256:lsD6hjAKLOdH/jqQZ28Ps0/1NLW5fW6/aV+nuwxn3gg`).
- No node files committed; docs only. Updated PHASE3_DE1_HIDDIFY_LIVE_VERIFY/NODES/PORTS/NETWORK/SECURITY/DEPLOYMENT/
  ROLLBACK/CURRENT_STATUS; new PHASE4_PRELIVE_DE1_TUNING.md.

## 2026-06-16 — Phase 4B: account/notification/idempotency + WAL-safe backup foundations — PASS

- **Backend-foundation / dry-run only** (stdlib). No platform sends, no real customers, no live Hiddify mutations, no
  services started; de1 stays `status=test`. See [PHASE4B_ACCOUNT_NOTIFICATION_BACKUP.md](PHASE4B_ACCOUNT_NOTIFICATION_BACKUP.md).
- **Additive migration** `0002_phase4b.sql`: `idempotency_keys` += `status`/`updated_at`; `outbound_messages` +=
  `payload_ref`/`last_error`/`next_attempt_at`/`max_attempts`; two indexes. No drops/rewrites; integrity + FK verified.
- **AccountService** (`backend/account_service.py`): `resolve_customer` maps a platform identity to ONE canonical
  customer (idempotent create + gap-safe `public_customer_code`); raw platform id is never the identity; validates the
  five platforms; `preferred_language` default `my`; transactional.
- **Account-link codes** (`backend/account_linking.py`): one-time 8-char codes, 24h expiry, **hash-only** storage,
  **reason-opaque** validation; consume = link / already-linked no-op / **merge_required_dry_run (no mutation)**.
- **NotificationService** (`backend/notification_service.py`): queue-first `enqueue` (default `queued`),
  retry/dead-letter helpers, placeholder per-platform `classify_policy`. **No sender; no raw body stored** (payload_ref).
- **Idempotency** (`backend/idempotency.py`): `begin`/`complete` with `started`/`already_completed`/`in_progress`
  states, stable replay; scopes payment_approval/provision_subscription/referral_grant/account_link_merge.
  `backend/payment_flow.py` is a **dry-run** boundary proving exactly-once (no subscription/access rows, no Hiddify).
- **WAL-safe backup** (`backend/backup.py`, `bin/backup_db.py`): `sqlite3.Connection.backup()` only (never raw-copies
  WAL); verifies integrity + FK on the snapshot; sanitized manifest (paths only, env contents never read). No timer yet.
- New CLIs: `bin/backup_db.py`, `bin/queue_notifications.py` (audit/dry-run), `bin/account_service_smoke.py` (temp DB).
- **Tests: 48 PASS** (17 Phase 4A + 31 new). Updated DATABASE/ACCOUNT_LINKING/BACKUPS/BOT_FLOWS/SECURITY/DEPLOYMENT/
  CURRENT_STATUS/BRAIN_API_DESIGN; new PHASE4B doc.

## 2026-06-16 — Phase 4A: DB foundation + Hiddify client/provisioner (dry-run) — PASS

- **Stdlib-only** backend foundation (sqlite3/urllib/unittest — no pip on the control plane). No live mutations, no
  real customers, no services started; de1 stays `status=test`.
- Schema (`backend/migrations/0001_initial.sql`, FK-enforced): all required tables incl. `proxy_nodes` provenance
  split (est_/det_/conf_), subscription order-time snapshots, idempotency_keys, outbound_messages, etc.
  Idempotent runner `backend/migrate.py` + `schema_migrations`. `bin/init_db.py` = migrate+seed.
- Seed catalogue (admin-editable, not code constants): plans TRIAL/BASIC_1M/CORE_1M/PLUS_3M/PRO_3M/MAX_6M with the
  authoritative GiB/days/MMK; regions de(default)/us/sg(premium-only); profiles FAST1/FAST2/SECURE; entitlements
  (SG only on PRO/MAX; Fast-label rule); de1 node `status=test` with detected specs.
- `backend/hiddify/client.py`: verified API v2 endpoints, `Hiddify-API-Key` header, **GiB→GB at the boundary**,
  no secret/URL/payload logging, structured results, timeouts/retries, injectable opener (tests mock it).
- `bin/hiddify_customer_provisioner.py`: audit/status/validate-contract/provision-one/suspend-one/reconcile-usage —
  **dry-run by default; live double-gated** (env latch + `--live --confirm`); sanitized output.
- **Tests: 17 PASS** (`python3 -m unittest discover -s tests`). New PHASE4A_DB_BACKEND_FOUNDATION.md, BRAIN_API_DESIGN.md
  (design-only), updated DATABASE/CURRENT_STATUS.

## 2026-06-16 — Add consolidated SOURCE_OF_TRUTH.md (Custom-GPT upload file) + generator

- New `scripts/build_source_of_truth.sh` assembles `SOURCE_OF_TRUTH.md` (repo root) from the canonical living docs
  (invariants + CURRENT_STATUS + DECISIONS/ADRs + verified Hiddify contract + recent CHANGELOG + server inventory).
- **This is the file to upload to the Custom GPT** as its instruction/source-of-truth — NOT `IMPLEMENTATION_PLAN.md`
  (that's the static v1.9 plan). Regenerate after each task (`bash scripts/build_source_of_truth.sh`), commit, then
  re-download from GitHub and re-upload to the GPT. Secret-free (derived from already-committed docs).

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
  `PHASE2_DE1_OS_UPGRADE.md`, `CURRENT_STATUS`. Docs only.

## 2026-06-15 — Phase 2-DE: OS-to-22.04 path decided = clean reinstall (no in-place upgrade)

- Ran a **read-only pre-upgrade gate** on `de1` (SSH OK; 20.04.6; 18 GB free; RAM 3.1 GiB + 1.9 GiB swap; apt/dpkg
  healthy & unlocked; only SSH:22 + 80/443 free; clean; **`reboot-required` flag set**). Gate **PASS** (upgrade
  feasible).
- **Decision (Charles): clean provider reinstall to Ubuntu 22.04, NOT in-place `do-release-upgrade`** — `de1` is
  empty, so reinstall is the same end-state with far less risk (in-place over SSH could drop SSH/brick the node, and
  its failure mode is a reinstall anyway). **No upgrade command run; no node changes.**
- New `PHASE2_DE1_OS_UPGRADE.md` (gate result + decision/rationale + operator reinstall steps incl. re-add key +
  known_hosts refresh). Updated `CURRENT_STATUS`, `PHASE2_DE1_PREFLIGHT`, `PHASE2_3_DE_NODE_PLAN`. Docs only.
- **Next:** Charles reinstalls to 22.04 + re-adds the Master key → agent re-runs Phase 2-DE preflight → Phase 3-DE.

## 2026-06-15 — Clarify de1 preflight blocker + reinstall requirement (docs audit)

- Audited all DE docs for the Phase 2-DE finding (PARTIAL; clean node; detected specs; OS-mismatch blocker). Most was
  already recorded in the prior commit. **Gap patched:** made the **host-key-change → `known_hosts` refresh** point
  explicit (alongside the existing re-add-public-key note) in `PHASE2_DE1_PREFLIGHT.md` and `CURRENT_STATUS.md` — the
  reinstall changes the node's SSH host key, so the Master must `ssh-keygen -R 5.249.160.59` / re-pin on next connect
  (host-key-mismatch warning expected, not an attack). Docs only.

## 2026-06-15 — Phase 2-DE: de1 SSH verified + clean preflight — PARTIAL (OS = 20.04)

- Root key SSH to `de1` now **works** (key-only, host key pinned). Ran a **read-only** node-facts preflight (no
  writes/installs/changes on the node).
- **Detected (authoritative, ADR-002):** Ubuntu **20.04.6** LTS / kernel 5.4 (hostname `white-cobra-75504`); 4 vCPU
  (Xeon E5-2690 v4); **3.1 GiB RAM** (+1.9 GiB swap); 25 GB disk (18 GB free); `eth0 5.249.160.59`, egress matches;
  only SSH:22 public, 80/443 free; **no firewall**; nginx/docker/certbot absent; **legacy scan CLEAN**.
- **Estimate vs detected:** CPU ✓, disk ✓, IP ✓; **RAM under** (3.1 vs 4 GB); **OS MISMATCH** (20.04 vs required 22.04).
- **Result: PARTIAL — blocker is OS.** `de1` must be **reinstalled to Ubuntu 22.04 LTS** (then re-add the Master key,
  re-run preflight) before the Hiddify host install. Node hardening (disable password login, firewall) deferred to
  Phase 3-DE. New report `PHASE2_DE1_PREFLIGHT.md`; updated SERVERS/NODES/NETWORK/PORTS/DEPLOYMENT/SECURITY/
  CURRENT_STATUS. Docs only.

## 2026-06-15 — de1 SSH connectivity test — PARTIAL/HOLD (key not yet authorized)

- Tested Master→`de1` SSH with the dedicated key (`/root/.ssh/unseenproxy_de1_ed25519`, `IdentitiesOnly`,
  `BatchMode`, `accept-new`, `ConnectTimeout=10`). **Node reachable** (handshake OK, host key pinned) but
  **`Permission denied (publickey)`** for **both** `root@5.249.160.59` and `ubuntu@5.249.160.59` — the public key is
  not in `authorized_keys` yet. No brute-force, no password login, no node changes.
- **Action for Charles (run on `de1` via provider console):**
  `mkdir -p /root/.ssh && chmod 700 /root/.ssh && echo 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIABHKgQZkRTmmQw5D0ECI+SljBYeCBqXSoOLwDttg7be unseen-proxy-master-to-de1' >> /root/.ssh/authorized_keys && chmod 600 /root/.ssh/authorized_keys`
  (for a `ubuntu`-only image, run the same under `/home/ubuntu/.ssh` owned by `ubuntu`). Then re-run the connectivity test.

## 2026-06-15 — Prepared Master→de1 SSH key (no connection yet)

- Generated a dedicated ed25519 keypair on the Master for `de1`: `/root/.ssh/unseenproxy_de1_ed25519` (private
  `600`, root-only) / `.pub` (`644`), comment `unseen-proxy-master-to-de1`, fingerprint
  `SHA256:jUYAdY0ONdXKzOg2s4OKO27yBGqLvBwapkEy25oA3+I`. Private key stays on the Master, never in git.
- **Action for Charles:** add the **public** key in the VPS provider panel before first login. No SSH/connection to
  `de1` performed. Reconciled the key path in `PHASE2_3_DE_NODE_PLAN.md`. Docs only.

## 2026-06-15 — Requirement: future Master cleanup of co-location leftovers (ADR-003)

- Recorded **[DECISIONS.md](DECISIONS.md) ADR-003** ("Master minimalism and cleanup of abandoned co-location
  dependencies"): the Master is control-plane only; anything installed solely for the retired co-location path is a
  **cleanup candidate**. The idle **Docker engine** (leftover from the failed Hiddify-on-Master test) is the primary
  candidate, to be removed in a **future audited "Master cleanup after retired co-location attempt" task** — **not
  now**, and not during node onboarding.
- Documented the pre-removal verification gate (no containers/volumes/deps, no docs/scripts need Docker, no Hiddify
  remnants, 80/443 free, SSH untouched) and a backup-first rule (snapshot or git-clean + service-state backup).
- Added cleanup-candidate notes to `DEPLOYMENT`, `SECURITY`, `ROLLBACK`, `SERVERS`, `CURRENT_STATUS`,
  `PHASE3_HIDDIFY_LIVE_VERIFY`, and a "not during onboarding" note to `PHASE2_3_DE_NODE_PLAN`. **Docs only — nothing
  uninstalled, no services touched.**

## 2026-06-15 — Requirement: verify ACTUAL node specs at onboarding (ADR-002)

- Recorded **[DECISIONS.md](DECISIONS.md) ADR-002**: provider/purchase specs are **estimates only**; on real node
  onboarding the Master must collect the node's **actual** facts via **read-only** SSH probes (no mutation, no
  secrets) and treat detected values as authoritative.
- Established per-value **provenance tiers**: `estimate` / `detected` / `provider-confirmed` / `unknown`. Bandwidth
  stays `estimate` until `provider-confirmed`. Verify before Hiddify install + re-check after if usage changes;
  role-fit (disk/RAM sufficient) gated before install.
- Documented the future read-only probe (`scripts/node_preflight_probe.sh`) in `PHASE2_3_DE_NODE_PLAN.md` (facts to
  detect: OS/kernel/CPU/RAM/disk/public-IP/route/ports/firewall/service-presence/clean-check/role-fit). **Written/run
  only when Phase 2-DE begins — not now.**
- Labelled `de1` specs as **provider-estimate (unverified)** in `SERVERS.md`/`NODES.md`/`CURRENT_STATUS.md`; added
  notes to `DEPLOYMENT.md` (verify-before-install) and `SECURITY.md` (probe is read-only, no secrets, don't trust
  manual specs). **Docs only — no node connection.**

## 2026-06-15 — Decision: Master control-plane-only; DE node → separate VPS (ADR-001)

- Recorded **[DECISIONS.md](DECISIONS.md) ADR-001**: the §4.1 **co-location exception is RETIRED**. The Master is
  **control-plane only** (no proxy traffic); the DE Hiddify node moves to a **dedicated separate VPS**.
- New DE node `de1` registered in inventory: **`5.249.160.59`**, 4 vCPU / 4 GB / 25 GB SSD / 30 TB, **Ubuntu 22.04**,
  `status=test`, domain `node-de.unseen.click` — to be provisioned by Hiddify's **supported host installer**.
- New `PHASE2_3_DE_NODE_PLAN.md` (forward workflow: preflight, Master→node SSH key, DNS plan, host install, live
  Swagger/API verify, disposable test user, FAST1/FAST2/Secure checks).
- Updated ARCHITECTURE / SYSTEM_OVERVIEW / SERVERS / NODES / NETWORK / PORTS (co-location retired; Master never
  proxies; 80/443 conflict resolved by separation), DEPLOYMENT / ROLLBACK / SECURITY / HIDDIFY_API_CONTRACT
  (point to the DE VPS host install), and marked PHASE2/PHASE3 docs superseded/historical. `IMPLEMENTATION_PLAN.md`
  left as source-history; the decision lives in `DECISIONS.md`. **Docs only — no node connection, no install.**

## 2026-06-15 — Phase 3 (Hiddify Docker install attempt — PARTIAL/BLOCKED)

- With Charles's authorization (snapshot confirmed), the agent ran the **official pinned Docker install
  (v12.3.3)** from `/opt` → isolated `/opt/hiddify-manager`. Docker 29.5.3 installed; 3 containers came up.
- **Host stayed safe:** SSH:22 up throughout; iptables INPUT policy `ACCEPT` (Docker added only its own
  NAT/FORWARD chains; Hiddify firewall left OFF); only 80/443 published (bridge); project git clean.
- **Panel is NON-FUNCTIONAL:** 443 returns no response; logs show a **Redis AUTH mis-wiring** + **DB migration
  errors**; the `hiddifypanel` CLI **hangs** on app import. MariaDB reachable, `admin_user` row exists, but the
  web/API never started. → **Live API/Swagger/contract verification BLOCKED; no test user created.** No destructive
  fix attempted (conservative mandate). Empirically confirms the official "Docker not for permanent use" caveat.
- Secret-safe throughout: no admin link generated/printed/committed; install log `0600`; scratch removed.
- Updated `PHASE3_HIDDIFY_LIVE_VERIFY.md` (actual result), `CURRENT_STATUS`, `HIDDIFY_API_CONTRACT`, `NODES`,
  `SERVERS`, `PORTS`, `DEPLOYMENT`.
- **Decision (Charles): tear down + separate DE VPS.** Removed the broken stack (`docker compose down -v` + deleted
  `/opt/hiddify-manager`); Master back to baseline (SSH up, 80/443 free, INPUT ACCEPT; Docker engine kept).
  **Root cause confirmed:** compose `$REDIS_PASSWORD` interpolation bug (Redis ran password-less while the panel used
  a password). **DE node will move to a separate Ubuntu-22.04 VPS** via Hiddify's supported host installer — DE is no
  longer the §4.1 co-location exception; the Master stays control-plane-only.

## 2026-06-15 — Phase 3 (Hiddify live-verify PREP — operator install pending)

- **No install performed by the agent; no Hiddify API call; no system change.** Docs/scripts only.
- B2 provider snapshot **confirmed by Charles**; co-location-via-Docker chosen.
- Ran the **read-only pre-install safety gate** → **PASS** (git clean, SSH:22 listening, 80/443 free, no firewall,
  ~13 GiB RAM / 86 GB disk free, legacy-clean, Master ports free). Verified the environment is capable (root,
  internet) but **cannot hold an SSH-recovery session/console**; the official Docker install is **experimental +
  long-running**. Decision: **operator installs, agent verifies after**.
- Verified the **current official Docker install command** (`bash <(curl https://i.hiddify.com/docker/<version>)`;
  it installs Docker itself) and the official caveat: **Docker version "not recommended for permanent use"** — OK
  for a test node; engine revisited before any live promotion.
- New `PHASE3_HIDDIFY_LIVE_VERIFY.md` (operator runbook + safety-gate evidence + live-verify checklist + sanitized
  contract placeholders) and `scripts/phase3_post_install_probe.sh` (read-only, secret-free post-install probe).
  Updated `CURRENT_STATUS`, `HIDDIFY_API_CONTRACT`, `PHASE3_HIDDIFY_AUDIT_PLAN`, `DEPLOYMENT`, `NODES`.
  Status: **PARTIAL / HOLD** — node remains `status=test`.

## 2026-06-15 — Phase 3 (Hiddify install & API audit PLAN)

- **Read-only research only — no install, no Hiddify API call, no system change.** Docs-only.
- Researched official/primary Hiddify sources (hiddify.com docs, DeepWiki, GitHub) and produced
  `PHASE3_HIDDIFY_AUDIT_PLAN.md` with tiered findings (**[VERIFIED]** / **[LIVE]** / **[ASSUMPTION]**).
- **Verified:** install path `/opt/hiddify-manager`; standard install brings nginx+HAProxy+Xray+sing-box+MariaDB+
  Redis and **takes 80/443**; **Docker** install can **remap ports and run behind an existing nginx**; firewall is
  **iptables, Hiddify-managed**; API v2 base paths + `Hiddify-API-Key: <admin-UUID>` header auth; official OS is
  **22.04** (24.04 had Redis-7.0 install issues, since fixed — Docker bundles Redis and sidesteps it).
- **B1 resolvable:** recommended **Option A** (Docker behind Master nginx) or **Option C** (separate DE VPS, lowest
  risk); proxy inbounds (Hysteria2/Reality/SS) need dedicated ports (not HTTP-proxyable). **B3** firewall/SSH-safety
  plan documented. **B4** reduced but exact ports/units/API fields remain **[LIVE]**. **B2** snapshot still manual.
- Updated `HIDDIFY_API_CONTRACT` (base/auth now docs-verified; CRUD/fields **[LIVE]**), `PORTS`, `NETWORK`,
  `DEPLOYMENT`, `ROLLBACK`, `SECURITY`, `PHASE2_…PREFLIGHT`, `CURRENT_STATUS`. Readiness: **PARTIAL / HOLD**.

## 2026-06-15 — Phase 2 (protected Master/DE Hiddify preflight)

- **Read-only preflight only — Hiddify NOT installed; no system changes made** (no nginx/docker/certbot/ufw/
  package/systemd/firewall/DB/`.env` changes).
- Inspected the Master: 4 vCPU / 15 GiB RAM (~13 GiB free) / 4 GiB swap / 86 GB free disk — sufficient for a
  co-located **test** DE node.
- Confirmed ports 80/443 and Master loopback ports 8190/8191/8192/8197 are currently **free**; only SSH:22 is
  public. **No active host firewall** (ufw inactive, iptables all-ACCEPT, empty nft).
- Legacy scan **CLEAN** (only the authorized `HIDDIFY_API_CONTRACT.md` matched `*hiddify*`).
- Identified the central co-location blocker: **80/443 + TLS ownership** must be decided before install; a
  **provider snapshot is required** before the invasive installer touches the live control plane.
- Readiness decision: **PARTIAL / HOLD** — install authorized only after B1–B4 prerequisites.
- New doc `PHASE2_MASTER_DE_HIDDIFY_PREFLIGHT.md`; updated SERVERS/NODES/PORTS/NETWORK/DEPLOYMENT/ROLLBACK and
  marked `HIDDIFY_API_CONTRACT.md` ports as not-verified-until-Phase-3.

## 2026-06-15 — Phase 0 + Phase 1

- Phase 0 clean-VPS verification signed off: **PASS** (gate passed before any build).
- Git repository initialized at the project root with a private origin (later pushed to `origin/main`, 25e5ddc).
- Added `.gitignore` and a pre-commit secret-scan hook.
- Added `.env.example` placeholder files (no real secrets).
- Created the full `docs/` skeleton per §32.
- Recorded naming and subdomain decisions in `DOMAINS.md`.

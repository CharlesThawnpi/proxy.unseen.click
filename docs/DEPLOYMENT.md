# DEPLOYMENT

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §31A.5
> **Status:** decided from plan; **Phase 4A backend foundation present.** DB init/update: `python3 bin/init_db.py
> --db <path>` (migrate+seed, idempotent). Tests: `python3 -m unittest discover -s tests`. Stdlib-only (no pip).
> Real `.env` placed on the Master only (from `.env.example`); DB lives under `data/` (git-ignored). Hiddify live
> provisioning is double-gated (`UNSEENPROXY_HIDDIFY_PROVISION_LIVE_ENABLED=1` + `--live --confirm`) — not used yet.

How UNSEEN PROXY is deployed: a manual **pull onto the Master**, never a push-to-server. Secrets and data stay on the Master; git delivers code only.

## Timezone

The project business timezone is **Myanmar Time (MMT, UTC+06:30, `Asia/Yangon`)**. Deployment, portal, bot, payment,
invoice, subscription, and report examples should use MMT unless a value is explicitly a technical UTC log timestamp.
Current app-created dry-run business timestamp writes route through `backend.timezone`; legacy SQLite `datetime('now')`
defaults remain documented migration fallbacks and should be audited before live launch. Use
`python3 bin/timezone_audit.py backend docs/TIMEZONE_POLICY.md` as a sanitized local check when touching timestamp
code or docs.

## Deploy key on the Master

- The Master holds a deploy key for the private repo; its **private half stays on the Master and never enters the
  repo**. Stored per the secret rules: `0600`, root-owned.

### Current setup (2026-06-15)

- **Origin (SSH):** `git@github.com:CharlesThawnpi/proxy.unseen.click.git`.
- **Deploy key:** `/root/.ssh/unseenproxy_github_deploy_ed25519` (private `600`, public `644`); `github.com` host
  key pinned in `/root/.ssh/known_hosts` (`StrictHostKeyChecking=yes`).
- **Access level:** this key currently has **write** access (added to the repo's GitHub deploy keys), used so the
  Master can push its own project docs/code commits. The plan's §31A.5 *read-only* intent is a future tightening
  option once a separate CI/build path publishes commits; revisit when that exists.
- **Pull/push command:**
  `GIT_SSH_COMMAND='ssh -i /root/.ssh/unseenproxy_github_deploy_ed25519 -o IdentitiesOnly=yes' git <pull|push>`.

## Deploy = pull, not push-to-server

On the Master, into the working tree `/opt/unseen-proxy/`:

1. `git pull` (or `git checkout` a milestone tag).
2. Run migrations (§30A.1 schema-migrations registry — ordered, forward-only, idempotent).
3. Restart the affected systemd units.

## `scripts/deploy.sh` (gated)

A short script documents the exact, gated steps — **dry-run first** wherever it mutates anything:

`pull → backup DB+.env → migrate → restart → verify`

The DB+`.env` backup before migrating is mandatory (see [BACKUPS.md](BACKUPS.md)).

> Verified in Phase 10

## Secrets and DB are NOT delivered by git

- `.env` and the SQLite DB already live on the Master; git never carries them.
- On a **fresh clone**, the operator must place `.env` (copied from `.env.example` and filled in with real values) **before services start**.

## Database backups (Phase 4B — script ready, no timer yet)

- WAL-safe online backup exists: `python3 bin/backup_db.py --db <db> --out-dir <dir> [--dry-run]` — uses
  `sqlite3.Connection.backup()`, verifies `integrity_check` + `foreign_key_check`, writes a sanitized manifest
  (paths only). See [BACKUPS.md](BACKUPS.md).
- **Production hardening is deferred to Phase 10:** root-only (mode 700) backup dir, retention, a systemd timer, and
  capturing the `.env`(s) **together** with the DB (so encrypted tokens stay decryptable). No timer/unit was created
  in Phase 4B; do not enable an automated backup until that gated task.

## Portal HTTP boundary (Phase 8C — local-only, no public deployment)

The portal HTTP adapter (`backend/portal_http.py` + `portal_middleware`/`portal_cookies`/`portal_csrf`/
`rate_limit`/`access_log`/`sidecar_boundary`) is a **deployment boundary only**. As of Phase 8C it is
**not deployed**: there is no running web server, no nginx, no TLS, no systemd unit, and no public bind.

- **No persistent service.** Nothing starts on import or during request dispatch; the adapter is exercised
  entirely in-memory by tests and smokes.
- **Loopback-only preview tool.** `python3 bin/portal_local_preview_server.py --serve-local` binds **only**
  `127.0.0.1` (default), refuses `0.0.0.0` (exit 2), starts nothing without `--serve-local`, uses a fresh
  temp DB, and creates no systemd/nginx/TLS. It is an operator dev convenience, never an enabled service.
- **Public deployment is a separate, gated task.** Enabling nginx/TLS + systemd + a public bind for the
  portal and the `sub.unseen.click` sidecar must not precede the de1 rebuild (live provisioning stays
  blocked until then). Decide the shared rate-limit store and the CSRF signing-key source from secret
  config before any public bind. See [PHASE8C_PORTAL_HTTP_DEPLOYMENT_BOUNDARY.md](PHASE8C_PORTAL_HTTP_DEPLOYMENT_BOUNDARY.md).

## Nodes are NOT deployed from git

- Node VPS run **stock Hiddify Manager**; only the Master pulls project code.
- A node is configured/orchestrated by the Master over the Hiddify API v2 — not by a git checkout.
- **DE node = separate VPS (co-location retired, [DECISIONS.md](DECISIONS.md) ADR-001).** Hiddify is **not** installed
  on the Master. The DE node (`5.249.160.59`, Ubuntu 22.04) is provisioned by Hiddify's **supported host installer**
  on its own VPS, configured/orchestrated from the Master over API v2 — never by `git pull`. Workflow:
  [PHASE2_3_DE_NODE_PLAN.md](PHASE2_3_DE_NODE_PLAN.md).
- **Verify node specs before install ([DECISIONS.md](DECISIONS.md) ADR-002).** Purchase specs are estimates; the
  preflight runs a read-only node-facts probe and records **detected** values (OS/CPU/RAM/disk/ports), confirming
  role-fit (enough disk/RAM for Hiddify) **before** the installer runs, and re-checking after if usage changes.
- **Master stays minimal ([DECISIONS.md](DECISIONS.md) ADR-003).** Docker engine on the Master is now an **unused
  leftover** from the failed Hiddify-on-Master test and is a **cleanup candidate** — to be removed in a future audited
  "Master cleanup after retired co-location attempt" task (verify no containers/volumes/deps, 80/443 free, SSH
  untouched, git-clean/backup first), **not** during node onboarding.

### Hiddify install method (Phase 3 audit, tiered)

- **[VERIFIED]** Two methods: host `install.sh` (brings nginx/HAProxy/Xray/sing-box/MariaDB/Redis to the host) or
  **Docker** (containerized; bundles Redis/MariaDB). Install path **`/opt/hiddify-manager/`** — separate from
  `/opt/unseen-proxy/`, no collision.
- **[VERIFIED]** Official OS is **Ubuntu 22.04**; **24.04** (this Master) hit Redis-7.0 install-order issues since fixed
  — **not officially blessed**. **Docker bundles its own Redis, sidestepping that** → favored for the 24.04 Master.
- **Recommendation for co-location:** **Docker install with remapped ports behind the Master nginx (Option A)**, OR a
  **separate DE VPS (Option C)**. Both pin a known-good version. **Standard host install is NOT recommended on the
  control plane** (it would seize 80/443 and mutate the host broadly).
- Install is host-level and gated on the **B2 provider snapshot** + the live-verify checklist — never run blind.
- **[VERIFIED] Current official Docker install command** (the script installs Docker itself; pin a version, don't use
  `latest`): `bash <(curl https://i.hiddify.com/docker/<version>)` (e.g. `…/docker/v12.3.3`). Internally it runs
  `common/docker-installer.sh`, creates `./hiddify-manager` in the **CWD** (run from `/opt`), and brings up a 3-container
  stack (hiddify + mariadb + redis, bridge mode, only 80/443 published, `privileged`+`NET_ADMIN`).
- **[VERIFIED-LIVE, 2026-06-15] The v12.3.3 Docker build did NOT produce a working panel** on this 24.04 Master:
  Redis AUTH mis-wiring + first-boot DB migration errors left 443 not serving and the CLI hanging. Confirms Hiddify's
  **"Docker not recommended for permanent use"** caveat. **Decision taken (ADR-001): the DE node uses the supported
  host install on Ubuntu 22.04 on a separate VPS** (`5.249.160.59`). See [PHASE3_HIDDIFY_LIVE_VERIFY.md](PHASE3_HIDDIFY_LIVE_VERIFY.md)
  and [PHASE2_3_DE_NODE_PLAN.md](PHASE2_3_DE_NODE_PLAN.md).
- **Done (2026-06-16):** `de1` reinstalled to Ubuntu 22.04.5; **Hiddify v12.3.3 host install completed & running**
  via `download.sh v12.3.3 --no-gui` (version-pinned, non-interactive). Lesson: run installers under the **default
  umask (022)** — a restrictive umask broke perms and needed remediation. See
  [PHASE3_DE1_HIDDIFY_LIVE_VERIFY.md](PHASE3_DE1_HIDDIFY_LIVE_VERIFY.md).

## de1 pre-live tuning status (Phase 4, 2026-06-16)

de1 was hardened test-safe ([PHASE4_PRELIVE_DE1_TUNING.md](PHASE4_PRELIVE_DE1_TUNING.md)): firewall verified (no change
needed — Hiddify nf_tables ACCEPTs precede ufw; SSH:22 allowed), **SSH password login disabled** (root key-only kept,
verified), services healthy, host key pinned. **Live is BLOCKED until rebuild:** the leaked default-user/server keys
have no safe surgical regen, so before de1 serves real customers it must be rebuilt (provider reinstall Ubuntu 22.04 →
re-add Master key → preflight → fresh Hiddify host install under umask 022 → re-apply SSH hardening → fresh
least-privilege service admin API key → disposable-user verify → only then Charles-gated `live`). de1 stays `status=test`.

## Phase 4C — dry-run provisioning CLIs (2026-06-16)

Backend dry-run orchestration is wired ([PHASE4C_DRY_RUN_PROVISIONING.md](PHASE4C_DRY_RUN_PROVISIONING.md)) and runnable
on a temp DB: `bin/approve_payment_dry_run.py`, `bin/provision_subscription_dry_run.py`,
`bin/provisioning_flow_smoke.py`. All are dry-run; **live Hiddify provisioning is hard-disabled** (refuses even with
`UNSEENPROXY_HIDDIFY_PROVISION_LIVE_ENABLED=1 --live --confirm`). Enabling live is a future, separately-gated task
**after** the de1 rebuild (clears the leaked-key blocker) and a real-device protocol PASS.

## Phase 5 — Telegram bot foundation (dry-run; not started, 2026-06-16)

The bot foundation exists ([PHASE5_TELEGRAM_BOT_FOUNDATION.md](PHASE5_TELEGRAM_BOT_FOUNDATION.md)) but is **not a running
service**: no polling, no webhook, no Telegram API call, no send, no systemd unit, no public endpoint. Dry-run tools run
on a temp DB: `bin/telegram_bot_smoke.py`, `bin/render_telegram_messages.py`. Env names (values in `.env` on the Master
ONLY): `TELEGRAM_BOT_TOKEN`, `ADMIN_TELEGRAM_IDS` (fallback alias `TELEGRAM_ADMIN_IDS`). Starting a real bot (gated
long-poll + NotificationService sender) is a future task; live sends require `ALLOW_LIVE_BOT_SENDS` + explicit flags and
remain disabled in Phase 5.

## Phase 5 transport — gated, not started (2026-06-16)

The transport foundation exists ([PHASE5_TELEGRAM_TRANSPORT_FOUNDATION.md](PHASE5_TELEGRAM_TRANSPORT_FOUNDATION.md)) but
**nothing runs**: no polling daemon, no webhook, no Telegram API call, no send, no systemd unit, no public endpoint.
Dry-run tools (temp DB / mock): `bin/telegram_poll_dry_run.py`, `bin/outbound_worker_dry_run.py`,
`bin/send_notification_dry_run.py`. Env gate names (values in `.env` on the Master ONLY): `ALLOW_LIVE_BOT_SENDS`,
`ALLOW_LIVE_BOT_POLLING` (default `0`). Going live requires BOTH the env latch `=1` AND `--live-send`/`--live-poll
--confirm`, a real network opener, and (for provisioning) the de1 rebuild — all a future, Charles-gated task.

## Phase 6 — subscription delivery foundation (dry-run; not wired to a node, 2026-06-16)

The delivery foundation exists ([PHASE6_SUBSCRIPTION_DELIVERY_FOUNDATION.md](PHASE6_SUBSCRIPTION_DELIVERY_FOUNDATION.md))
but fetches nothing from de1 and sends nothing: Hiddify output is **mocked** in tests/CLIs. Dry-run tools (temp DB):
`bin/subscription_delivery_smoke.py`, `bin/render_delivery_dry_run.py`. The branded customer link
(`https://sub.unseen.click/s/<token>`) and its resolving **sidecar** are a future, gated task — the sidecar will fetch
the real node subscription **in memory** (`access_log off`) and never persist raw links. Live delivery requires the de1
rebuild + a real-device protocol PASS + the Phase 5 live send gate — all Charles-gated.

## Phase 7 — entitlement + node-resilience resolver (dry-run; no node contacted, 2026-06-16)

The resolver layer ([PHASE7_ENTITLEMENT_NODE_RESILIENCE.md](PHASE7_ENTITLEMENT_NODE_RESILIENCE.md)) is DB-driven and
read-only: it never contacts a node, fetches metrics, or marks anything live. Dry-run tools (temp DB):
`bin/entitlement_audit.py`, `bin/availability_preview.py`, `bin/node_resilience_smoke.py` (uses mock alerts).
Node health is derived from `node_alerts`; populating those from real read-only probes (a health monitor) is a future,
sanitized task. Live candidate selection (status=live + healthy + no `node_live_blockers`) stays gated behind the de1
rebuild + the global `phase4c_live_disabled` switch.

## Phase 7 — health monitor (single-pass, not scheduled, 2026-06-16)

The monitor ([PHASE7_HEALTH_MONITOR_FOUNDATION.md](PHASE7_HEALTH_MONITOR_FOUNDATION.md)) is invoked **once** by a CLI;
there is **no daemon, no systemd timer/service**. Dry-run tools (temp DB; mock probes):
`bin/node_health_probe_dry_run.py` (`--real-public-tcp-only` opts into read-only public TCP), `bin/node_health_monitor_once.py`
(`--write-metrics` writes only to the explicit `--db`), `bin/node_alerts_preview.py`. A **gated** periodic scheduler
(cron/timer) running `monitor_once --write-metrics` against the live DB — plus a read-only SSH metrics collector once a
node is live — is a future, separately-authorized task. No node is modified; no secrets are fetched.

## Phase 8 — customer portal foundation (render-only, not deployed, 2026-06-16)

The portal foundation exists ([PHASE8_WEB_PORTAL_FOUNDATION.md](PHASE8_WEB_PORTAL_FOUNDATION.md), [PORTAL.md](PORTAL.md))
but is **not deployed**: no web server, no nginx/TLS, no systemd unit, no public endpoint, and no real auth. Dry-run
tools default to a fresh temp DB/sample data:

- `python3 bin/portal_smoke.py`
- `python3 bin/portal_render_dry_run.py --page plans`
- `python3 bin/portal_render_dry_run.py --page subscription --out /tmp/unseen_portal_subscription.html`

A real portal deployment is a future gated task requiring a public HTTP boundary, short-lived portal auth, `/s/`
resolution, secret-safe access logging, and live delivery integration. It remains blocked from real provisioning until
the de1 rebuild and real-device protocol PASS.

### Phase 8A local preview export

For visual review only:

`python3 bin/portal_preview_export.py --out-dir tmp/portal-preview`

This writes static HTML under git-ignored `tmp/portal-preview/` and prints page names + file paths only. The exporter
uses a fresh temp DB/sample data by default, refuses output outside repo `tmp/`, starts no server, and performs no
network calls. Generated preview files are not deployment artifacts and must not be committed.

### Phase 8B portal auth/session foundation

Phase 8B adds hash-only token/session DB tables and helpers, but **still deploys nothing**. `bin/portal_auth_smoke.py`
and `bin/portal_token_dry_run.py` use temp DB/sample data by default and print only sanitized summaries. A real portal
deployment still needs a future HTTP adapter, cookie-setting middleware, rate limits, access logging policy, and `/s/`
live-resolution sidecar review before any public exposure. Portal access/session service-created timestamps are stored
as MMT-aware strings via `backend.timezone`; schema defaults are fallback-only.

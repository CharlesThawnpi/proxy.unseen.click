# DEPLOYMENT

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §31A.5
> **Status:** decided from plan; **Phase 4A backend foundation present.** DB init/update: `python3 bin/init_db.py
> --db <path>` (migrate+seed, idempotent). Tests: `python3 -m unittest discover -s tests`. Stdlib-only (no pip).
> Real `.env` placed on the Master only (from `.env.example`); DB lives under `data/` (git-ignored). Hiddify live
> provisioning is double-gated (`UNSEENPROXY_HIDDIFY_PROVISION_LIVE_ENABLED=1` + `--live --confirm`) — not used yet.

How UNSEEN PROXY is deployed: a manual **pull onto the Master**, never a push-to-server. Secrets and data stay on the Master; git delivers code only.

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

# DEPLOYMENT

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §31A.5
> **Status:** Phase 1 skeleton — decided from plan

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

## Nodes are NOT deployed from git

- Node VPS run **stock Hiddify Manager**; only the Master pulls project code.
- A node is configured/orchestrated by the Master over the Hiddify API v2 — not by a git checkout.
- **Co-located DE node:** installing Hiddify on the Master itself is a **manual, host-level, snapshot-gated**
  operation — explicitly **not** part of `git pull` deploy. It is on HOLD pending the preflight prerequisites
  (`PHASE2_MASTER_DE_HIDDIFY_PREFLIGHT.md`) and the Phase 3 decision (`PHASE3_HIDDIFY_AUDIT_PLAN.md`).

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

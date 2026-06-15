# DEPLOYMENT

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §31A.5
> **Status:** Phase 1 skeleton — decided from plan

How UNSEEN PROXY is deployed: a manual **pull onto the Master**, never a push-to-server. Secrets and data stay on the Master; git delivers code only.

## Deploy key on the Master

- The Master holds a **read-only deploy key** (or a fine-scoped deploy token) for the private repo `https://github.com/CharlesThawnpi/proxy.unseen.click.git`.
- It is least-privilege; its **private half stays on the Master and never enters the repo**.
- Generated/stored per the secret rules: `0600`, root-owned.

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

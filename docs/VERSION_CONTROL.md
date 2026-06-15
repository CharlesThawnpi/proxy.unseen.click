# VERSION CONTROL

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §31A
> **Status:** Phase 1 skeleton — decided from plan

How UNSEEN PROXY uses GitHub: one authorized private repo, secrets kept out by construction, manual pull-to-deploy.

## The one authorized repository

- **Private repo:** `https://github.com/CharlesThawnpi/proxy.unseen.click.git`.
- Private so architecture, configs, and component layout are not public.
- This is the **one authorized repository**, and it does **not** violate clean-build isolation. That rule forbids referencing the **retired UNSEEN VPN** repos/artifacts only. This fresh repo *is* the UNSEEN PROXY project — the tooling builds into it and pushes to it, and never pulls from or matches against any legacy repo.
- Local working tree: `/opt/unseen-proxy/`, with `origin` set to the URL above.

## Tracked vs. NEVER tracked

**Tracked (in git):** application code, migration files, `docs/`, the implementation plan, `.env.example` files (placeholders only), systemd unit *templates*, nginx site *templates*, `requirements.txt`/lockfiles, and `seed_catalogue.py` (seeds structure and starting values only, no secrets).

**NEVER tracked (enforced by `.gitignore` + pre-commit scan):**
- `.env` and any real secret (bot token, `ACCESS_TOKEN_ENCRYPTION_SECRET`, node API keys, panel admin paths, Reality private keys/short-ids).
- The database (`*.sqlite3`, WAL/SHM files) and all backups.
- Anything under `data/`, `backups/`, `logs/`, `tmp/`, generated QR images, or any file that could contain tokens, subscription URLs, screenshots, or PII.

## `.gitignore` + pre-commit secret scan

- `.gitignore` covers everything in the "NEVER tracked" list.
- A **pre-commit hook** scans staged changes for secret-shaped strings (token/key patterns, `hiddify://` / `vless://` / `ss://` / `hy2://`, `/s/<token>` URLs, long UUID payloads, full IPs) and **blocks the commit** if found.
- The hook lives at `scripts/pre-commit-secret-scan.sh`, wired in via `.githooks/pre-commit`.
- **Enable it on a fresh clone:**

  ```sh
  git config core.hooksPath .githooks
  ```

This operationalizes the standing rule "secrets never enter git" (§31 rules 1 & 9) so it can't be violated by accident.

## Branching & history (§31A.4)

- **`main` is always deployable.** Day-to-day work happens on short-lived feature branches merged into `main`; small solo commits directly to `main` are acceptable early on.
- Commits are **descriptive and reference the phase/section** (e.g. "Phase 5: Telegram bot register flow").
- Every change updates `docs/` + `CHANGELOG.md` — the changelog is the human-readable history, git is the precise one.
- **Tag releases at milestones** (e.g. `v-internal-beta`, `v-soft-launch`) so a known-good code state can be re-deployed quickly. Git history is also a rollback tool (see [ROLLBACK.md](ROLLBACK.md)).

## Committed secret = incident

A committed secret is treated as a **security incident**: rotate the exposed secret (§30A.5, see [SECRET_ROTATION.md](SECRET_ROTATION.md)) — don't just delete the commit.

## CI (deferred)

Automated CI/CD is **intentionally not enabled at start** (manual pull is simpler and lower-risk). A later optional step may add **GitHub Actions for checks only** (lint + unit tests on push), with **deployment staying manual**. Auto-deploy from CI to the Master is out of scope unless explicitly chosen later, because it would put deploy credentials in GitHub and risk an unattended change to a live system. See [DEPLOYMENT.md](DEPLOYMENT.md).

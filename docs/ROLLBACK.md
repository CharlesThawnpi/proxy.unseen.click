# ROLLBACK

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §30.4, §31A.4
> **Status:** Phase 1 skeleton — decided from plan

How to safely undo a change. Code rollback and data rollback are **separate** mechanisms.

## Rollback discipline (§30.4)

- **Dry-run before every live mutation.** Every destructive tool ships `dry-run` / `status` / `audit` subcommands.
- **Pre-apply DB backup** before any schema change or bulk mutation (see [BACKUPS.md](BACKUPS.md)).
- Live actions are **double-gated**: env latch + explicit `--live --confirm` flags.
- **Prefer reversible actions:** disable (not delete) Hiddify users; rotate (not just revoke) tokens; mark a node test/standby (not destroy) to drain it.
- **Test on non-live nodes first.** New protocols/regions are validated with disposable users before any customer is routed there.

## Code rollback via git (§31A.4)

- Git history is a **code-rollback tool**: a bad code change is reverted by checking out a previous commit/tag and **re-pulling on the Master**.
- Milestone **tags** (e.g. `v-internal-beta`, `v-soft-launch`) mark known-good code states for quick redeploy.
- **Code rollback does NOT touch the DB.** The database has its own backup/restore path (§30.3). Reverting code and restoring data are independent operations — never conflate them.

## Data rollback

- Data is restored from the WAL-safe backups (DB + `.env` together; see [BACKUPS.md](BACKUPS.md)).
- After any restore, run the no-send token-decrypt smoke test before reporting success.

## Restore drill

> Verified in Phase 10

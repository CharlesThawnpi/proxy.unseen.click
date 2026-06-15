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

## Co-located Hiddify install on the Master (special rollback case)

Installing Hiddify Manager on the **Master** (the §4.1 co-located DE node) is **host-wide and invasive**: the
installer changes nginx, systemd units, packages, and may modify the firewall — on a **non-disposable** control
plane. The standard "disable, don't delete / re-pull a git tag" rollback does **not** cover host-level damage.

- **A provider/VPS snapshot taken immediately BEFORE install is the required rollback path.** In-place uninstall
  is not trusted to restore the prior state. Snapshot → install → if the control plane destabilizes, restore the
  snapshot.
- Git (`origin/main`) independently protects project code/docs; the DB (when it exists) has its own §30.3 backup.
  Neither substitutes for the host snapshot.
- The DE node starts `status=test` and is never auto-promoted, so a bad install affects only the test node, not
  customer-facing live service.
- Full readiness conditions and the snapshot prerequisite are in `PHASE2_MASTER_DE_HIDDIFY_PREFLIGHT.md`.

## Restore drill

> Verified in Phase 10

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

## Co-located Hiddify install on the Master — SUPERSEDED (co-location retired)

> **[DECISIONS.md](DECISIONS.md) ADR-001:** the DE node now runs on its **own VPS**, so Hiddify is never installed on
> the Master and this "host-wide install on the control plane" rollback case **no longer applies**. The DE node uses
> the **ordinary node rollback** (rebuild/re-provision from the Master; a fresh node VPS is disposable, so a snapshot
> is optional). The text below is retained as history of the attempted co-location.

Installing Hiddify Manager on the **Master** (the former §4.1 co-located DE node) is **host-wide and invasive**: the
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
- **[VERIFIED, Phase 3] Docker install is materially easier to roll back** (`docker compose down -v` + remove the
  Docker state) than a host `install.sh` (which mutates nginx/HAProxy/MariaDB/Redis/iptables host-wide). The provider
  snapshot (B2) remains mandatory regardless; Docker just narrows the blast radius. See
  [PHASE3_HIDDIFY_AUDIT_PLAN.md](PHASE3_HIDDIFY_AUDIT_PLAN.md).
- **SSH-lockout safety:** Hiddify manages iptables itself. Before relying on it, confirm SSH:22 from a **second
  session** post-install and keep a **provider console/recovery** path — a firewall misstep must not be unrecoverable.

## Master cleanup (ADR-003) — backup before host package removal

The future "Master cleanup after retired co-location attempt" task ([DECISIONS.md](DECISIONS.md) ADR-003) removes
unused leftovers (e.g. the idle Docker engine). Because it changes **host packages on the protected control plane**,
take a **provider snapshot** — or at minimum a **git-clean tree + a recorded service/package-state backup** — first,
run removals dry-run/audited, verify no dependency breaks (containers/volumes/deps, 80/443 free, SSH up), and **stop +
report** on anything unexpected. Rollback = restore the snapshot / re-install the package.

## DE node `de1` rollback (Hiddify installed 2026-06-16)

`de1` is a fresh **test** node with no customer data and the Master has no dependency on it yet (Phase 4 not started).
Rollback for a bad Hiddify state: `bash /opt/hiddify-manager/uninstall.sh` (official) or a **provider reinstall** of
Ubuntu 22.04 (then re-add the Master key + re-run preflight + reinstall Hiddify under the default umask). No snapshot
needed — nothing to preserve. See [PHASE3_DE1_HIDDIFY_LIVE_VERIFY.md](PHASE3_DE1_HIDDIFY_LIVE_VERIFY.md).

## Restore drill

> Verified in Phase 10

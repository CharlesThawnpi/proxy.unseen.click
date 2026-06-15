# BACKUPS

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §30.3
> **Status:** Phase 1 skeleton — decided from plan

How UNSEEN PROXY backs up its data safely: WAL-correct DB snapshots taken together with the secrets needed to decrypt them.

## WAL-safe DB snapshots

- A daily backup timer runs a Python backup using **`sqlite3.Connection.backup()`**.
- **Never `cp` the WAL DB.** Copying the live WAL/SHM files yields a stale or corrupt snapshot. The `conn.backup()` API produces a consistent point-in-time copy.
- Each snapshot is checked with `PRAGMA integrity_check`.

## DB and `.env` are backed up TOGETHER

- Durable subscription tokens decrypt **only** with `.env`'s `ACCESS_TOKEN_ENCRYPTION_SECRET`. A DB-only restore cannot decrypt them.
- Therefore the backup captures the **DB and the `.env`(s) together** — losing `ACCESS_TOKEN_ENCRYPTION_SECRET` makes every stored token permanently undecryptable.

## What is backed up

- The SQLite DB (via `conn.backup()`).
- The `.env`(s) — held together with the DB.
- systemd unit files.
- nginx site configs.
- The verified Hiddify API contract doc.

## What is NOT backed up

- **Test nodes carry no backup.** Backups live on the Master only; node VPS run stock Hiddify Manager and hold no project state worth restoring.

## Storage, retention, verification

- Root-only backup directory, mode **700**.
- Retention window (e.g. 14 days).
- `PRAGMA integrity_check` on every snapshot.
- After **any restore**, run a no-send token-decrypt smoke test to confirm `.env` and DB still match.

## Backup script

> Verified in Phase 4/10

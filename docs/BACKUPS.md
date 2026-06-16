# BACKUPS

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §30.3
> **Status:** **Phase 4B — backup script IMPLEMENTED (no production timer yet).** WAL-safe online backup + verify +
> sanitized manifest exist and are tested; the systemd timer/retention land in Phase 10.

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

## Backup script (Phase 4B — implemented)

`backend/backup.py` + `bin/backup_db.py` implement the WAL-safe online backup:

```
python3 bin/backup_db.py --db <db> --out-dir <dir> [--dry-run] [--include-env-path <path>]
```

- **`sqlite3.Connection.backup()` only** — a consistent point-in-time snapshot; the `.sqlite3`/`-wal`/`-shm` files
  are **never** raw-copied.
- Every snapshot is verified: `PRAGMA integrity_check` must be `ok` **and** `PRAGMA foreign_key_check` must be empty
  (the CLI exits non-zero otherwise).
- `--dry-run` plans the target paths and writes nothing.
- `--include-env-path` records the `.env` **path only** as manifest metadata. This slice **never reads or prints**
  `.env` contents (`env_contents_backed_up: false`); capturing the env value alongside the DB (so encrypted tokens stay
  decryptable) is a later, explicitly-authorized production step.
- A sanitized JSON manifest is written next to the snapshot — **paths and check results only, never secret values**.

**Production (Phase 10, not built yet):** root-only backup dir (mode **700**), retention window, a systemd timer, and
capturing the `.env`(s) together with the DB. No timer/unit was created in Phase 4B.

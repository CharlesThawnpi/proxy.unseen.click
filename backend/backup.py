"""WAL-safe online DB backup (§30.3, docs/BACKUPS.md).

Uses **`sqlite3.Connection.backup()`** to produce a consistent point-in-time snapshot of a
live WAL database. We NEVER raw-copy the `.sqlite3`/`-wal`/`-shm` files (that yields a stale or
corrupt snapshot). Every snapshot is verified with `PRAGMA integrity_check` and
`PRAGMA foreign_key_check`.

Secret-safety:
  - The `.env` is backed up TOGETHER with the DB in production (token-decrypt secret lives there),
    but this module records the env path as **path-only metadata** — it never reads or copies the
    env file contents unless a future, explicitly-authorized flag enables it. The manifest stores
    paths only, never values.
  - Production backup dir must be root-only (mode 700) — documented; not created by this module.
"""
from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import List, Optional


@dataclass
class BackupResult:
    ok: bool
    dry_run: bool
    db_path: str                       # source DB path (not a secret)
    backup_path: Optional[str]         # destination snapshot path (None for dry-run)
    manifest_path: Optional[str]
    integrity: Optional[str]           # 'ok' / failure text / None for dry-run
    fk_violations: int                 # count only; rows not surfaced
    env_path: Optional[str]            # path-only metadata; contents never read
    note: str = ""


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def verify_backup(path: str) -> tuple:
    """Open a snapshot and return (integrity_text, fk_violation_count)."""
    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        integrity = conn.execute("PRAGMA integrity_check;").fetchone()[0]
        fk = conn.execute("PRAGMA foreign_key_check;").fetchall()
        return integrity, len(fk)
    finally:
        conn.close()


def online_backup(db_path: str, out_dir: str, dry_run: bool = False,
                  include_env_path: Optional[str] = None,
                  read_env_contents: bool = False) -> BackupResult:
    """Take a WAL-safe online backup of `db_path` into `out_dir`.

    dry_run=True plans the snapshot (computes target paths, writes nothing) — used by tests and
    operators to preview. include_env_path is recorded as path-only metadata; `read_env_contents`
    is a hard no-op here (reserved for a future authorized path) and never used to print values.
    """
    stamp = _utc_stamp()
    base = f"unseenproxy-{stamp}"
    backup_path = os.path.join(out_dir, base + ".sqlite3")
    manifest_path = os.path.join(out_dir, base + ".manifest.json")

    # We NEVER read env contents in this module, regardless of the flag.
    env_path = include_env_path  # stored as a path string only

    if dry_run:
        return BackupResult(
            ok=True, dry_run=True, db_path=db_path, backup_path=None, manifest_path=None,
            integrity=None, fk_violations=0, env_path=env_path,
            note="dry-run: no snapshot written; would use sqlite3.Connection.backup()",
        )

    os.makedirs(out_dir, exist_ok=True)

    src = sqlite3.connect(db_path)
    dest = sqlite3.connect(backup_path)
    try:
        # The online backup API — consistent point-in-time copy across WAL.
        src.backup(dest)
    finally:
        dest.close()
        src.close()

    integrity, fk_count = verify_backup(backup_path)

    manifest = {
        "created_at_utc": stamp,
        "db_path": db_path,                  # path only
        "backup_path": backup_path,
        "env_path": env_path,                # path only; contents NEVER read/stored
        "env_contents_backed_up": False,     # this slice: DB-only; env captured separately in prod
        "method": "sqlite3.Connection.backup()",
        "integrity_check": integrity,
        "foreign_key_violations": fk_count,
        "note": "WAL-safe online backup. Production: store in a root-only (700) dir alongside "
                "the .env so encrypted tokens remain decryptable. No secret values in this manifest.",
    }
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)

    return BackupResult(
        ok=(integrity == "ok" and fk_count == 0),
        dry_run=False, db_path=db_path, backup_path=backup_path, manifest_path=manifest_path,
        integrity=integrity, fk_violations=fk_count, env_path=env_path,
        note="online backup complete",
    )


def result_summary(result: BackupResult) -> str:
    """Sanitized one-line summary safe to print/log."""
    d = asdict(result)
    return json.dumps({k: d[k] for k in (
        "ok", "dry_run", "db_path", "backup_path", "integrity", "fk_violations", "env_path", "note")})

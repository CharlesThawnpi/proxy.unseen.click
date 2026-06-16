#!/usr/bin/env python3
"""WAL-safe online DB backup CLI (docs/BACKUPS.md).

Uses sqlite3.Connection.backup() (never raw-copies WAL files), verifies the snapshot with
integrity_check + foreign_key_check, and writes a sanitized manifest (paths only, no secrets).

  python3 bin/backup_db.py --db /tmp/dev.sqlite3 --out-dir /tmp/backups --dry-run
  python3 bin/backup_db.py --db /tmp/dev.sqlite3 --out-dir /tmp/backups

--include-env-path records the .env PATH as metadata only; this CLI never reads/prints its
contents. Production backup dir must be root-only (mode 700).
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import backup, config  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="WAL-safe online SQLite backup (sanitized output).")
    ap.add_argument("--db", default=config.db_path(), help="source DB path")
    ap.add_argument("--out-dir", required=True, help="destination backup directory")
    ap.add_argument("--dry-run", action="store_true", help="plan only; write nothing")
    ap.add_argument("--include-env-path", default=None,
                    help="record this .env PATH as metadata only (contents never read)")
    args = ap.parse_args(argv)

    result = backup.online_backup(
        db_path=args.db, out_dir=args.out_dir, dry_run=args.dry_run,
        include_env_path=args.include_env_path,
    )
    print(backup.result_summary(result))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

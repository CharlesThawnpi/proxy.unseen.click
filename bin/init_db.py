#!/usr/bin/env python3
"""Initialize (or update) an UNSEEN PROXY SQLite DB: apply migrations + seed catalogue.

Idempotent and safe to re-run. Uses a temp/dev path unless --db is given.
  python3 bin/init_db.py --db /tmp/dev.sqlite3
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import config, db as dbmod, migrate, seed  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Migrate + seed an UNSEEN PROXY DB (idempotent).")
    ap.add_argument("--db", default=config.db_path())
    args = ap.parse_args(argv)
    applied = migrate.migrate_path(args.db)
    conn = dbmod.connect(args.db)
    seed.seed(conn)
    integ = "ok" if dbmod.integrity_ok(conn) else "FAILED"
    plans = conn.execute("SELECT COUNT(*) FROM plans").fetchone()[0]
    nodes = conn.execute("SELECT COUNT(*) FROM proxy_nodes").fetchone()[0]
    conn.close()
    print(f"db={args.db} migrations_applied={applied or '(up to date)'} integrity={integ} "
          f"plans={plans} nodes={nodes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

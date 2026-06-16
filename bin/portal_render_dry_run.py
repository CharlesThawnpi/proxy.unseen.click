#!/usr/bin/env python3
"""Render one customer portal page against a temp/sample DB. No server, no network, no live DB."""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import db as dbmod, migrate, portal_app, portal_viewmodels, seed  # noqa: E402


PAGES = {
    "home": "/",
    "plans": "/plans",
    "dashboard": "/customer/status",
    "subscription": None,
    "branded": "/s/example-opaque-token",
    "help": "/help",
    "unavailable": "/unavailable",
    "expired": "/expired",
    "not-found": "/not-found",
}


def _db_path(value: str | None) -> str:
    if value:
        return value
    return os.path.join(tempfile.mkdtemp(prefix="unseen_portal_"), "portal.sqlite3")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Render a portal page to stdout or a file (dry-run only).")
    ap.add_argument("--db", help="Optional temp DB path. Defaults to a fresh temp DB.")
    ap.add_argument("--page", choices=sorted(PAGES), default="home")
    ap.add_argument("--out", help="Optional output file path. If omitted, prints HTML to stdout.")
    args = ap.parse_args(argv)

    db_path = _db_path(args.db)
    migrate.migrate_path(db_path)
    conn = dbmod.connect(db_path)
    seed.seed(conn)
    sample = portal_viewmodels.sample_data(conn)
    path = PAGES[args.page] or f"/subscriptions/{sample['subscription_id']}"
    response = portal_app.render(conn, path, customer_id=sample["customer_id"])
    conn.close()

    if args.out:
        Path(args.out).write_text(response.body, encoding="utf-8")
        print(f"rendered {path} -> {args.out} status={response.status_code}")
    else:
        print(response.body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


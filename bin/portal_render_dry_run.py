#!/usr/bin/env python3
"""Render one customer portal page against a temp/sample DB. No server, no network, no live DB."""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import db as dbmod, migrate, portal_app, portal_auth, portal_viewmodels, seed  # noqa: E402


PAGES = {
    "home": "/",
    "plans": "/plans",
    "dashboard": "/customer/status",
    "subscription": None,
    "branded": "/s/<opaque-token>",
    "help": "/help",
    "unavailable": "/unavailable",
    "degraded": "/degraded",
    "expired": "/expired",
    "not-found": "/not-found",
}

REPO_ROOT = Path(__file__).resolve().parent.parent
SAFE_OUT_ROOT = (REPO_ROOT / "tmp").resolve()


def _db_path(value: str | None) -> str:
    if value:
        return value
    return os.path.join(tempfile.mkdtemp(prefix="unseen_portal_"), "portal.sqlite3")


def _safe_output_path(value: str) -> Path:
    out = Path(value).expanduser()
    if not out.is_absolute():
        out = REPO_ROOT / out
    out = out.resolve()
    if not (out == SAFE_OUT_ROOT or SAFE_OUT_ROOT in out.parents):
        raise SystemExit(f"refusing to write outside git-ignored tmp/: {out}")
    out.parent.mkdir(parents=True, exist_ok=True)
    return out


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
    context = portal_auth.synthetic_context(sample["customer_id"])
    path = PAGES[args.page] or f"/subscriptions/{sample['subscription_id']}"
    response = portal_app.render(conn, path, session_context=context)
    conn.close()

    if args.out:
        out = _safe_output_path(args.out)
        out.write_text(response.body, encoding="utf-8")
        print(f"{args.page} {out}")
    else:
        print(response.body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

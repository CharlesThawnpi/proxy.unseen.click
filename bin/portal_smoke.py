#!/usr/bin/env python3
"""Smoke-render all portal pages against temp/sample data. No server, no network, no live DB."""
from __future__ import annotations

import argparse
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import db as dbmod, migrate, portal_app, portal_viewmodels, seed  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Portal smoke render (dry-run temp DB only).")
    ap.add_argument("--db", help="Optional temp DB path. Defaults to a fresh temp DB.")
    args = ap.parse_args(argv)

    db_path = args.db or os.path.join(tempfile.mkdtemp(prefix="unseen_portal_smoke_"), "portal.sqlite3")
    migrate.migrate_path(db_path)
    conn = dbmod.connect(db_path)
    seed.seed(conn)
    sample = portal_viewmodels.sample_data(conn)
    paths = [
        "/",
        "/plans",
        "/customer/status",
        f"/subscriptions/{sample['subscription_id']}",
        "/s/example-opaque-token",
        "/help",
        "/unavailable",
        "/expired",
        "/not-found",
    ]
    for path in paths:
        response = portal_app.render(conn, path, customer_id=sample["customer_id"])
        assert "hiddify://" not in response.body
        assert "vless://" not in response.body
        assert "ss://" not in response.body
        assert "hy2://" not in response.body
        assert "/api/v2/" not in response.body
        print(f"{response.status_code} {path} bytes={len(response.body)}")
    conn.close()
    print("SMOKE_OK: portal rendered sanitized pages; no server started.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


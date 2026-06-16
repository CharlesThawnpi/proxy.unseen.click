#!/usr/bin/env python3
"""Smoke the portal /s token resolver + session helper with temp/sample data only."""
from __future__ import annotations

import argparse
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import db as dbmod, migrate, portal_access, portal_app, portal_viewmodels, seed  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Portal auth smoke (temp DB; no server/cookie setting).")
    ap.add_argument("--db", help="Optional temp DB path. Defaults to a fresh temp DB.")
    args = ap.parse_args(argv)

    db_path = args.db or os.path.join(tempfile.mkdtemp(prefix="unseen_portal_auth_"), "portal.sqlite3")
    migrate.migrate_path(db_path)
    conn = dbmod.connect(db_path)
    seed.seed(conn)
    sample = portal_viewmodels.sample_data(conn)
    issued = portal_access.issue_token(
        conn,
        customer_id=sample["customer_id"],
        subscription_id=sample["subscription_id"],
    )
    response = portal_app.render(conn, f"/s/{issued.raw_token}")
    assert issued.raw_token not in response.body
    assert issued.token_hash not in response.body
    print({
        "resolver_status": response.status_code,
        "token_fingerprint": issued.fingerprint,
        "body_bytes": len(response.body),
        "raw_values_rendered": False,
    })
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Dry-run portal token issue/verify/revoke flow. Temp DB by default; raw token never printed."""
from __future__ import annotations

import argparse
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import db as dbmod, migrate, portal_access, portal_tokens, portal_viewmodels, seed  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Portal token dry-run (hash-only DB storage).")
    ap.add_argument("--db", help="Optional temp DB path. Defaults to a fresh temp DB.")
    args = ap.parse_args(argv)

    db_path = args.db or os.path.join(tempfile.mkdtemp(prefix="unseen_portal_token_"), "portal.sqlite3")
    migrate.migrate_path(db_path)
    conn = dbmod.connect(db_path)
    seed.seed(conn)
    sample = portal_viewmodels.sample_data(conn)
    issued = portal_access.issue_token(
        conn,
        customer_id=sample["customer_id"],
        subscription_id=sample["subscription_id"],
    )
    verified = portal_access.verify_token(conn, issued.raw_token)
    portal_access.revoke_token(conn, issued.token_id)
    revoked = portal_access.verify_token(conn, issued.raw_token)
    print({
        "token": portal_tokens.redact(issued.raw_token),
        "fingerprint": issued.fingerprint,
        "stored_hash_len": len(issued.token_hash),
        "verify": verified.reason,
        "after_revoke": revoked.reason,
    })
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


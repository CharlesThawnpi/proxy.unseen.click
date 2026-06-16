#!/usr/bin/env python3
"""Smoke-exercise the sidecar boundary against a temp DB. No live Hiddify, no network, no server.

Verifies branded tokens through the dry-run sidecar boundary and prints sanitized status lines.
Proves the boundary returns safe placeholders and never emits the raw token or live subscription
output.
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import (  # noqa: E402
    db as dbmod,
    migrate,
    portal_access,
    portal_viewmodels,
    rate_limit,
    seed,
    sidecar_boundary,
)

_FORBIDDEN = ("hiddify://", "vless://", "ss://", "hy2://", "/api/v2/")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Sidecar boundary smoke (dry-run temp DB only).")
    ap.add_argument("--db", help="Optional temp DB path. Defaults to a fresh temp DB.")
    args = ap.parse_args(argv)

    db_path = args.db or os.path.join(tempfile.mkdtemp(prefix="unseen_sidecar_smoke_"), "portal.sqlite3")
    migrate.migrate_path(db_path)
    conn = dbmod.connect(db_path)
    seed.seed(conn)
    sample = portal_viewmodels.sample_data(conn)

    issued = portal_access.issue_token(
        conn, customer_id=sample["customer_id"], subscription_id=sample["subscription_id"]
    )
    limiter = rate_limit.RateLimiter(max_attempts=3, window_seconds=60, block_seconds=120)

    cases = [
        ("valid", issued.raw_token),
        ("invalid", "not-a-real-token"),
    ]
    for name, token in cases:
        result = sidecar_boundary.handle_branded(conn, token, rate_limiter=limiter)
        assert result.fetched_live is False, "sidecar must not fetch live in Phase 8C"
        for needle in _FORBIDDEN:
            assert needle not in result.body
        line = sidecar_boundary.sanitized_access_line("198.51.100.7", result)
        assert token not in line, "raw token must never appear in access line"
        print(f"{name:10s} status={result.status_code} reason={result.reason} log='{line}'")

    conn.close()
    print("SMOKE_OK: sidecar boundary verified tokens; no live Hiddify fetch; no server started.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

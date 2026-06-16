#!/usr/bin/env python3
"""Smoke-exercise the portal HTTP adapter against a temp DB. No server, no socket, no network.

Builds HttpRequest objects in memory, runs them through PortalHttpApp, and prints sanitized
status lines. Proves routing + access-log sanitization without binding any port.
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
    portal_cookies,
    portal_http,
    portal_viewmodels,
    seed,
)

_FORBIDDEN = ("hiddify://", "vless://", "ss://", "hy2://", "/api/v2/", "unseen_portal_session=")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Portal HTTP adapter smoke (dry-run temp DB only).")
    ap.add_argument("--db", help="Optional temp DB path. Defaults to a fresh temp DB.")
    args = ap.parse_args(argv)

    db_path = args.db or os.path.join(tempfile.mkdtemp(prefix="unseen_http_smoke_"), "portal.sqlite3")
    migrate.migrate_path(db_path)
    conn = dbmod.connect(db_path)
    seed.seed(conn)
    sample = portal_viewmodels.sample_data(conn)
    app = portal_http.PortalHttpApp(conn)

    # A valid session cookie for the private routes (temp DB only).
    issued = portal_access.issue_token(
        conn, customer_id=sample["customer_id"], subscription_id=sample["subscription_id"]
    )
    from backend import branded_link_resolver, portal_sessions  # noqa: E402
    branded_link_resolver.resolve(conn, issued.raw_token)
    created = portal_sessions.create_session(conn, customer_id=sample["customer_id"])
    cookie = portal_cookies.build_session_set_cookie(created.raw_session_id).split(";", 1)[0]

    cases = [
        ("home", "GET", "/", None),
        ("plans", "GET", "/plans", None),
        ("help", "GET", "/help", None),
        ("dashboard-noauth", "GET", "/dashboard", None),
        ("dashboard-auth", "GET", "/dashboard", cookie),
        ("subscription-auth", "GET", "/subscription", cookie),
        ("branded-bad", "GET", "/s/not-a-real-token", None),
        ("expired", "GET", "/expired", None),
        ("not-found", "GET", "/zzz", None),
        ("method", "POST", "/", None),
    ]
    for name, method, path, cookie_val in cases:
        headers = {"Cookie": cookie_val} if cookie_val else {}
        request = portal_http.HttpRequest.build(method, path, headers=headers, remote_addr="203.0.113.9")
        response = app.handle(request)
        for needle in _FORBIDDEN:
            assert needle not in response.body, f"forbidden token in body for {name}"
        line = app.access_line(request, response)
        for needle in _FORBIDDEN:
            assert needle not in line, f"forbidden token in access line for {name}"
        assert "not-a-real-token" not in line
        print(f"{name:20s} status={response.status_code} log='{line}'")

    conn.close()
    print("SMOKE_OK: portal HTTP adapter routed sanitized responses; no server started.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

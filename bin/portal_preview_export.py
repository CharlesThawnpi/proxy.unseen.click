#!/usr/bin/env python3
"""Export sanitized portal preview HTML files under tmp/portal-preview. No server/network/live DB."""
from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import db as dbmod, migrate, portal_app, portal_viewmodels, seed  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
SAFE_OUT_ROOT = (REPO_ROOT / "tmp").resolve()
DEFAULT_OUT = SAFE_OUT_ROOT / "portal-preview"

FORBIDDEN = (
    "Hiddify-API-Key",
    "/api/v2/",
    "vless://",
    "ss://",
    "hy2://",
    "hiddify://",
    "node-de.unseen.click",
)
UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)


def _safe_dir(value: str | None) -> Path:
    out = Path(value).expanduser() if value else DEFAULT_OUT
    if not out.is_absolute():
        out = REPO_ROOT / out
    out = out.resolve()
    if not (out == SAFE_OUT_ROOT or SAFE_OUT_ROOT in out.parents):
        raise SystemExit(f"refusing to write outside git-ignored tmp/: {out}")
    out.mkdir(parents=True, exist_ok=True)
    return out


def _fresh_db(value: str | None) -> str:
    if value:
        return value
    return os.path.join(tempfile.mkdtemp(prefix="unseen_portal_preview_"), "portal.sqlite3")


def _assert_sanitized(html: str) -> None:
    for needle in FORBIDDEN:
        if needle in html:
            raise AssertionError(f"forbidden preview content: {needle}")
    if UUID_RE.search(html):
        raise AssertionError("forbidden UUID-shaped value in preview")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Export portal preview HTML files (temp DB; no server).")
    ap.add_argument("--db", help="Optional temp DB path. Defaults to a fresh temp DB.")
    ap.add_argument("--out-dir", help="Output directory under repo tmp/. Defaults to tmp/portal-preview.")
    args = ap.parse_args(argv)

    out_dir = _safe_dir(args.out_dir)
    db_path = _fresh_db(args.db)
    migrate.migrate_path(db_path)
    conn = dbmod.connect(db_path)
    seed.seed(conn)
    sample = portal_viewmodels.sample_data(conn)
    portal_viewmodels.add_preview_degraded_state(conn)

    pages = [
        ("home", "/"),
        ("plans", "/plans"),
        ("dashboard", "/customer/status"),
        ("subscription", f"/subscriptions/{sample['subscription_id']}"),
        ("branded-placeholder", "/s/<opaque-token>"),
        ("help", "/help"),
        ("unavailable", "/unavailable"),
        ("degraded", "/degraded"),
        ("expired", "/expired"),
        ("not-found", "/not-found"),
    ]
    for name, path in pages:
        response = portal_app.render(conn, path, customer_id=sample["customer_id"])
        _assert_sanitized(response.body)
        target = out_dir / f"{name}.html"
        target.write_text(response.body, encoding="utf-8")
        print(f"{name} {target}")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

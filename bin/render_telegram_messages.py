#!/usr/bin/env python3
"""Render the Burmese-primary message catalogue + DB-driven plan view (TEMP DB; no send).

A safe way to eyeball the bot copy without a Telegram connection. Prints catalogue strings and
the plan list rendered from DB seed rows. No token/admin id/secret is read or printed.

  python3 bin/render_telegram_messages.py --db /tmp/tg_render.sqlite3
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import bot_flows, db as dbmod, migrate, seed, telegram_messages as msg  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Render Telegram message catalogue (no send).")
    ap.add_argument("--db", default="/tmp/unseenproxy_tg_render.sqlite3")
    args = ap.parse_args(argv)

    migrate.migrate_path(args.db)
    conn = dbmod.connect(args.db)
    seed.seed(conn)

    print("=== WELCOME ===\n" + msg.WELCOME)
    print("\n=== MAIN MENU ===\n" + msg.MAIN_MENU)
    print("\n=== HELP ===\n" + msg.help_text())
    print("\n=== PLANS (from DB seed) ===\n" + bot_flows.build_plans_view(conn))
    print("\n=== LINK PROMPT ===\n" + msg.LINK_PROMPT)
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

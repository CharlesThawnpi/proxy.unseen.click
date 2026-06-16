"""Bot flow content builders — DB-driven, dry-run (§6 plan rendering, BOT_FLOWS).

These compose Burmese-primary copy (telegram_messages) with **DB rows** — plan values and
entitlements are read from the catalogue/seed, never hardcoded in the bot. No secrets, links,
UUIDs, or QR payloads are produced.
"""
from __future__ import annotations

import sqlite3
from typing import List

from . import display, seed, telegram_messages as msg


def build_plans_view(conn: sqlite3.Connection) -> str:
    """Render the public plan list from DB rows + DB entitlements (DE default, SG premium-only,
    FAST display rule). Never hardcodes plan values."""
    rows = conn.execute(
        "SELECT plan_code, display_name_en, data_limit_gib, duration_days, price_mmk "
        "FROM plans WHERE is_public=1 AND is_enabled=1 ORDER BY sort_order"
    ).fetchall()
    lines: List[str] = [msg.PLANS_HEADER]
    for r in rows:
        regions = seed.entitled_regions(conn, r["plan_code"])
        profiles = seed.entitled_profiles(conn, r["plan_code"])
        labels = display.fast_labels(profiles)
        premium = [reg for reg in regions if conn.execute(
            "SELECT is_premium_only FROM proxy_regions WHERE region_code=?", (reg,)).fetchone()[0] == 1]
        lines.append(msg.plan_line(
            r["display_name_en"], r["plan_code"], int(r["data_limit_gib"]),
            int(r["duration_days"]), int(r["price_mmk"]), regions, labels, premium))
    return "\n".join(lines)


def build_account_status(conn: sqlite3.Connection, customer_id: int, public_code: str) -> str:
    """Sanitized subscription status for a customer (counts/states only — no tokens/links/UUIDs)."""
    subs = conn.execute(
        "SELECT plan_code, status, provision_status FROM subscriptions WHERE customer_id=? ORDER BY id",
        (customer_id,)).fetchall()
    if not subs:
        return msg.ACCOUNT_STATUS_NONE.format(code=public_code)
    lines = [msg.ACCOUNT_STATUS_HEADER.format(code=public_code)]
    for s in subs:
        lines.append(f"• {s['plan_code']}: {s['status']} / {s['provision_status']}")
    lines.append(msg.COMING_SOON)
    return "\n".join(lines)


def build_admin_summary(conn: sqlite3.Connection) -> str:
    """Dry-run operational summary from DB only — counts, no identities/secrets."""
    def _count(sql: str) -> int:
        return int(conn.execute(sql).fetchone()[0])
    return msg.admin_summary(
        customers=_count("SELECT COUNT(*) FROM customers"),
        subscriptions=_count("SELECT COUNT(*) FROM subscriptions"),
        queued_notifications=_count("SELECT COUNT(*) FROM outbound_messages WHERE status='queued'"),
        dry_run_attempts=_count("SELECT COUNT(*) FROM provisioning_attempts WHERE mode='dry_run'"),
    )

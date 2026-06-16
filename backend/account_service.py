"""AccountService — platform identity → one canonical customer (§9.3, ADR-aligned).

Resolves a platform identity (telegram/messenger/viber/whatsapp/web user id) to a single
canonical `customers.id`, creating the customer + `platform_accounts` mapping on first sight
and returning the existing one thereafter (idempotent). The **raw platform id is never the
customer identity** — it is only a lookup key in `platform_accounts`; identity is the internal
`customers.id` surfaced publicly as the gap-safe `public_customer_code` (e.g. UP0001).

No secrets are stored here. `profile` may carry a preferred language hint only; we do NOT
persist names/handles/PII (no such columns exist, by design).
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from . import db as _db
from .customer_code import assign_code_for_id

# The only platforms an account may resolve on. `web` exists solely for the bot-issued
# short-lived portal link (§16) — never an email/password account.
ALLOWED_PLATFORMS = ("telegram", "messenger", "viber", "whatsapp", "web")

DEFAULT_LANGUAGE = "my"  # Burmese-primary


class UnknownPlatformError(ValueError):
    """Raised when platform_name is not one of ALLOWED_PLATFORMS."""


def _validate_platform(platform_name: str) -> None:
    if platform_name not in ALLOWED_PLATFORMS:
        # Message names the field, never the value, to avoid echoing attacker-controlled input.
        raise UnknownPlatformError(f"platform_name must be one of {ALLOWED_PLATFORMS}")


def find_customer(conn: sqlite3.Connection, platform_name: str,
                  platform_user_id: str) -> Optional[int]:
    """Return the canonical customer_id for an existing platform account, else None."""
    _validate_platform(platform_name)
    row = conn.execute(
        "SELECT customer_id FROM platform_accounts WHERE platform_name=? AND platform_user_id=?",
        (platform_name, str(platform_user_id)),
    ).fetchone()
    return int(row[0]) if row else None


def resolve_customer(conn: sqlite3.Connection, platform_name: str, platform_user_id: str,
                     profile: Optional[dict] = None) -> int:
    """Resolve (or idempotently create) the canonical customer for a platform identity.

    - If the platform account exists → return its existing customer_id.
    - If missing → create a customer (gap-safe public_customer_code), attach the
      platform_accounts mapping, and return the new customer_id.
    Re-running with the same (platform_name, platform_user_id) is a no-op that returns
    the same id. All writes run in a single transaction.
    """
    _validate_platform(platform_name)
    platform_user_id = str(platform_user_id)

    existing = find_customer(conn, platform_name, platform_user_id)
    if existing is not None:
        return existing

    preferred_language = DEFAULT_LANGUAGE
    if profile and profile.get("preferred_language"):
        preferred_language = str(profile["preferred_language"])

    with _db.transaction(conn):
        # Re-check inside the transaction in case of a concurrent creator.
        again = conn.execute(
            "SELECT customer_id FROM platform_accounts WHERE platform_name=? AND platform_user_id=?",
            (platform_name, platform_user_id),
        ).fetchone()
        if again:
            return int(again[0])

        cur = conn.execute(
            "INSERT INTO customers(preferred_language) VALUES (?)",
            (preferred_language,),
        )
        customer_id = int(cur.lastrowid)
        # public_customer_code IS the gap-safe sequence: the row's own id (max-id+1 semantics).
        code = assign_code_for_id(customer_id)
        conn.execute(
            "UPDATE customers SET public_customer_code=?, referral_code=? WHERE id=?",
            (code, code, customer_id),
        )
        conn.execute(
            "INSERT INTO platform_accounts(platform_name, platform_user_id, customer_id) "
            "VALUES (?,?,?)",
            (platform_name, platform_user_id, customer_id),
        )
        return customer_id


def public_code(conn: sqlite3.Connection, customer_id: int) -> Optional[str]:
    row = conn.execute(
        "SELECT public_customer_code FROM customers WHERE id=?", (customer_id,)
    ).fetchone()
    return row[0] if row else None

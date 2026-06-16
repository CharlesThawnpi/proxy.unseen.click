"""Portal access-token model (dry-run/render-only Phase 8B).

Only token hashes are persisted. Raw tokens are returned once to the caller and must never be
logged, committed, or stored.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from . import db as _db, portal_tokens
from .audit import audit_row


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


def _dt(value: str | None) -> Optional[datetime]:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)


def _fmt(value: datetime) -> str:
    return value.replace(microsecond=0).isoformat(sep=" ")


@dataclass(frozen=True)
class IssuedPortalToken:
    token_id: int
    raw_token: str
    token_hash: str
    customer_id: int
    subscription_id: Optional[int]
    expires_at: str

    @property
    def fingerprint(self) -> str:
        return portal_tokens.fingerprint(self.raw_token)


@dataclass(frozen=True)
class PortalTokenVerification:
    valid: bool
    reason: str
    token_id: Optional[int] = None
    customer_id: Optional[int] = None
    subscription_id: Optional[int] = None
    access_profile_id: Optional[int] = None


def issue_token(
    conn: sqlite3.Connection,
    *,
    customer_id: int,
    subscription_id: int | None = None,
    access_profile_id: int | None = None,
    purpose: str = "branded_subscription",
    expires_at: str | None = None,
    now: datetime | None = None,
) -> IssuedPortalToken:
    now_dt = now or _utc_now()
    expiry = _dt(expires_at) if expires_at else now_dt + timedelta(hours=1)
    raw = portal_tokens.generate_opaque_token()
    handle = portal_tokens.hash_token(raw)
    with _db.transaction(conn):
        cur = conn.execute(
            "INSERT INTO portal_access_tokens"
            "(customer_id, subscription_id, access_profile_id, token_hash, purpose, status, expires_at) "
            "VALUES (?,?,?,?,?,'active',?)",
            (customer_id, subscription_id, access_profile_id, handle, purpose, _fmt(expiry)),
        )
        token_id = int(cur.lastrowid)
        audit_row(
            conn,
            "portal_token_issued",
            f"portal_access_token:{token_id}",
            f"customer:{customer_id} sub:{subscription_id} purpose:{purpose}",
            actor="system:portal",
        )
    return IssuedPortalToken(token_id, raw, handle, customer_id, subscription_id, _fmt(expiry))


def verify_token(
    conn: sqlite3.Connection,
    raw_token: str,
    *,
    now: datetime | None = None,
) -> PortalTokenVerification:
    handle = portal_tokens.hash_token(raw_token)
    row = conn.execute(
        "SELECT * FROM portal_access_tokens WHERE token_hash=?", (handle,)
    ).fetchone()
    if row is None:
        audit_row(conn, "portal_invalid_token", "portal_access_token:unknown",
                  "reason:unknown", actor="system:portal")
        conn.commit()
        return PortalTokenVerification(False, "unknown")
    if not portal_tokens.constant_time_equal(row["token_hash"], handle):
        audit_row(conn, "portal_invalid_token", f"portal_access_token:{row['id']}",
                  "reason:hash_mismatch", actor="system:portal")
        conn.commit()
        return PortalTokenVerification(False, "unknown")
    if row["revoked_at"] or row["status"] != "active":
        audit_row(conn, "portal_invalid_token", f"portal_access_token:{row['id']}",
                  "reason:revoked", actor="system:portal")
        conn.commit()
        return PortalTokenVerification(False, "revoked", token_id=int(row["id"]))
    now_dt = now or _utc_now()
    if _dt(row["expires_at"]) <= now_dt:
        audit_row(conn, "portal_invalid_token", f"portal_access_token:{row['id']}",
                  "reason:expired", actor="system:portal")
        conn.commit()
        return PortalTokenVerification(False, "expired", token_id=int(row["id"]))
    with _db.transaction(conn):
        conn.execute(
            "UPDATE portal_access_tokens SET last_verified_at=datetime('now') WHERE id=?",
            (row["id"],),
        )
        audit_row(conn, "portal_token_verified", f"portal_access_token:{row['id']}",
                  f"customer:{row['customer_id']} sub:{row['subscription_id']}", actor="system:portal")
    return PortalTokenVerification(
        True,
        "valid",
        token_id=int(row["id"]),
        customer_id=int(row["customer_id"]),
        subscription_id=int(row["subscription_id"]) if row["subscription_id"] is not None else None,
        access_profile_id=int(row["access_profile_id"]) if row["access_profile_id"] is not None else None,
    )


def revoke_token(conn: sqlite3.Connection, token_id: int) -> None:
    with _db.transaction(conn):
        conn.execute(
            "UPDATE portal_access_tokens SET status='revoked', revoked_at=datetime('now') WHERE id=?",
            (token_id,),
        )
        audit_row(conn, "portal_token_revoked", f"portal_access_token:{token_id}",
                  "reason:manual_or_test", actor="system:portal")

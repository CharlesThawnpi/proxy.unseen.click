"""Hash-only portal session helpers for Phase 8B.

This is not a live cookie/session service. It provides future-ready primitives and local tests
without starting a web server or setting cookies over HTTP.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from . import db as _db, portal_tokens
from .audit import audit_row

COOKIE_NAME = "unseen_portal_session"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


def _dt(value: str | None) -> Optional[datetime]:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)


def _fmt(value: datetime) -> str:
    return value.replace(microsecond=0).isoformat(sep=" ")


@dataclass(frozen=True)
class CreatedPortalSession:
    session_id: int
    raw_session_id: str
    session_hash: str
    customer_id: int
    expires_at: str

    @property
    def fingerprint(self) -> str:
        return portal_tokens.fingerprint(self.raw_session_id)


@dataclass(frozen=True)
class PortalSessionVerification:
    valid: bool
    reason: str
    session_id: Optional[int] = None
    customer_id: Optional[int] = None


@dataclass(frozen=True)
class PortalSessionContext:
    customer_id: int
    session_id: Optional[int] = None
    source: str = "synthetic"


def create_session(
    conn: sqlite3.Connection,
    *,
    customer_id: int,
    source_access_token_id: int | None = None,
    expires_at: str | None = None,
    now: datetime | None = None,
) -> CreatedPortalSession:
    now_dt = now or _utc_now()
    expiry = _dt(expires_at) if expires_at else now_dt + timedelta(hours=2)
    raw = portal_tokens.generate_opaque_token()
    handle = portal_tokens.hash_token(raw)
    with _db.transaction(conn):
        cur = conn.execute(
            "INSERT INTO portal_sessions"
            "(customer_id, source_access_token_id, session_hash, status, expires_at) "
            "VALUES (?,?,?,'active',?)",
            (customer_id, source_access_token_id, handle, _fmt(expiry)),
        )
        session_id = int(cur.lastrowid)
        audit_row(conn, "portal_session_created", f"portal_session:{session_id}",
                  f"customer:{customer_id} token:{source_access_token_id}",
                  actor="system:portal")
    return CreatedPortalSession(session_id, raw, handle, customer_id, _fmt(expiry))


def verify_session(
    conn: sqlite3.Connection,
    raw_session_id: str,
    *,
    now: datetime | None = None,
) -> PortalSessionVerification:
    handle = portal_tokens.hash_token(raw_session_id)
    row = conn.execute("SELECT * FROM portal_sessions WHERE session_hash=?", (handle,)).fetchone()
    if row is None:
        return PortalSessionVerification(False, "unknown")
    if not portal_tokens.constant_time_equal(row["session_hash"], handle):
        return PortalSessionVerification(False, "unknown")
    if row["revoked_at"] or row["status"] != "active":
        return PortalSessionVerification(False, "revoked", session_id=int(row["id"]))
    now_dt = now or _utc_now()
    if _dt(row["expires_at"]) <= now_dt:
        return PortalSessionVerification(False, "expired", session_id=int(row["id"]))
    with _db.transaction(conn):
        conn.execute("UPDATE portal_sessions SET last_verified_at=datetime('now') WHERE id=?", (row["id"],))
    return PortalSessionVerification(True, "valid", session_id=int(row["id"]), customer_id=int(row["customer_id"]))


def revoke_session(conn: sqlite3.Connection, session_id: int) -> None:
    with _db.transaction(conn):
        conn.execute(
            "UPDATE portal_sessions SET status='revoked', revoked_at=datetime('now') WHERE id=?",
            (session_id,),
        )
        audit_row(conn, "portal_session_revoked", f"portal_session:{session_id}",
                  "reason:manual_or_test", actor="system:portal")


def cookie_attributes(*, same_site: str = "Lax", secure: bool = True, path: str = "/") -> dict:
    same = same_site if same_site in {"Lax", "Strict"} else "Lax"
    return {"HttpOnly": True, "Secure": bool(secure), "SameSite": same, "Path": path}


def build_set_cookie_value(raw_session_id: str, *, max_age: int | None = None,
                           same_site: str = "Lax", secure: bool = True) -> str:
    attrs = cookie_attributes(same_site=same_site, secure=secure)
    parts = [f"{COOKIE_NAME}={raw_session_id}", "HttpOnly", f"SameSite={attrs['SameSite']}", f"Path={attrs['Path']}"]
    if attrs["Secure"]:
        parts.append("Secure")
    if max_age is not None:
        parts.append(f"Max-Age={int(max_age)}")
    return "; ".join(parts)

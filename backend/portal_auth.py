"""Portal auth boundary for Phase 8B render-only sessions.

This does not implement real login or a live cookie service. It centralizes the future route
guard semantics around `PortalSessionContext`.
"""
from __future__ import annotations

import sqlite3

from . import portal_sessions


class PortalAuthNotImplemented(RuntimeError):
    pass


def require_future_auth() -> None:
    """Placeholder guard for future HTTP integration."""
    raise PortalAuthNotImplemented("portal auth is not implemented in Phase 8")


def context_from_raw_session(conn: sqlite3.Connection, raw_session_id: str) -> portal_sessions.PortalSessionContext | None:
    verified = portal_sessions.verify_session(conn, raw_session_id)
    if not verified.valid or verified.customer_id is None:
        return None
    return portal_sessions.PortalSessionContext(
        customer_id=verified.customer_id,
        session_id=verified.session_id,
        source="session_cookie",
    )


def synthetic_context(customer_id: int) -> portal_sessions.PortalSessionContext:
    """Test/render helper; never a live authenticated customer session."""
    return portal_sessions.PortalSessionContext(customer_id=int(customer_id), source="synthetic")

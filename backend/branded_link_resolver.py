"""Branded `/s/<opaque-token>` resolver boundary (Phase 8B, dry-run/render-only)."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from . import portal_access, portal_sessions


@dataclass(frozen=True)
class BrandedLinkResolution:
    status: str
    customer_id: Optional[int] = None
    subscription_id: Optional[int] = None
    session_context: Optional[portal_sessions.PortalSessionContext] = None
    session_created: bool = False

    @property
    def valid(self) -> bool:
        return self.status == "valid"


def resolve(conn: sqlite3.Connection, raw_token: str, *, now: datetime | None = None) -> BrandedLinkResolution:
    checked = portal_access.verify_token(conn, raw_token, now=now)
    if not checked.valid:
        return BrandedLinkResolution(status=checked.reason)
    created = portal_sessions.create_session(
        conn,
        customer_id=checked.customer_id,
        source_access_token_id=checked.token_id,
        now=now,
    )
    context = portal_sessions.PortalSessionContext(
        customer_id=created.customer_id,
        session_id=created.session_id,
        source="branded_link",
    )
    return BrandedLinkResolution(
        status="valid",
        customer_id=checked.customer_id,
        subscription_id=checked.subscription_id,
        session_context=context,
        session_created=True,
    )


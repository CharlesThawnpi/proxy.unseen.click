"""Dry-run boundary for the future `sub.unseen.click` subscription sidecar (Phase 8C).

The live sidecar will eventually receive `/s/<opaque-token>`, verify the branded token, fetch the
real node subscription document from Hiddify in memory, and stream it to the customer's client —
WITHOUT ever persisting the raw Hiddify output. Phase 8C builds only the verification + response
boundary: it verifies the branded token (hash-backed, no session side effects) and returns a safe
placeholder. No live Hiddify fetch happens here, and access logging follows the off/sanitized
policy (the raw token is never logged).
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from . import access_log, portal_access, rate_limit

# Content type the real sidecar will eventually serve (subscription document).
SUBSCRIPTION_CONTENT_TYPE = "text/plain; charset=utf-8"
PLACEHOLDER_BODY = (
    "UNSEEN PROXY subscription sidecar (dry-run boundary)\n"
    "status: not-live\n"
    "note: live subscription resolution is blocked until de1 rebuild + real-device PASS.\n"
)


@dataclass(frozen=True)
class SidecarResult:
    status_code: int
    body: str
    reason: str
    content_type: str = SUBSCRIPTION_CONTENT_TYPE
    # The sidecar never persists raw Hiddify output; this stays False in Phase 8C.
    fetched_live: bool = False


def handle_branded(
    conn: sqlite3.Connection,
    raw_token: str,
    *,
    now: datetime | None = None,
    rate_limiter: rate_limit.RateLimiter | None = None,
) -> SidecarResult:
    """Verify a branded token and return a safe placeholder.

    Verification is hash-backed via portal_access (no session is minted here, no Hiddify call).
    On a valid token we return a placeholder document — the real node fetch is intentionally absent
    until live provisioning is unblocked.
    """
    if rate_limiter is not None:
        decision = rate_limiter.check(rate_limit.safe_key(raw_token, scope="sidecar"), now=now)
        if not decision.allowed:
            return SidecarResult(429, PLACEHOLDER_BODY, reason="rate_limited")

    checked = portal_access.verify_token(conn, raw_token, now=now)
    if not checked.valid:
        if checked.reason in {"expired", "revoked"}:
            return SidecarResult(410, PLACEHOLDER_BODY, reason=checked.reason)
        return SidecarResult(404, PLACEHOLDER_BODY, reason="not_found")
    # Valid token: live fetch is deliberately NOT performed; return the dry-run placeholder.
    return SidecarResult(200, PLACEHOLDER_BODY, reason="valid_placeholder", fetched_live=False)


def sanitized_access_line(remote_addr: str | None, result: SidecarResult, *, redact_ip: bool = True) -> str:
    """Build the sidecar's sanitized access line. The raw token is never an input here."""
    event = access_log.AccessEvent(
        method="GET",
        path="/s/<redacted>",
        status=result.status_code,
        remote_addr=remote_addr,
        redact_client_ip=redact_ip,
    )
    return access_log.format_access_event(event)

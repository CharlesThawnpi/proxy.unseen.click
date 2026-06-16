"""Secure cookie / response middleware helpers for the portal HTTP boundary (Phase 8C).

These helpers are framework-free and pure: they turn an inbound request's cookies into a verified
`PortalSessionContext` and attach hardened security headers to outbound responses. No socket, no
server, no live auth against production. The session lookup is hash-backed via portal_auth.
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from . import portal_auth, portal_cookies, portal_sessions


def security_headers(*, private: bool = False) -> dict[str, str]:
    """Baseline hardened response headers.

    `private=True` (dashboard/subscription/branded pages) adds no-store caching so customer state
    is never cached by shared proxies or the browser back/forward cache.
    """
    headers = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "no-referrer",
        "Content-Security-Policy": "default-src 'self'; img-src 'self' data:; style-src 'self'; "
                                   "base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
        "Cross-Origin-Opener-Policy": "same-origin",
    }
    if private:
        headers["Cache-Control"] = "no-store, max-age=0"
    else:
        headers["Cache-Control"] = "no-cache"
    return headers


def session_context_from_cookie_header(
    conn: sqlite3.Connection,
    cookie_header: str | None,
) -> Optional[portal_sessions.PortalSessionContext]:
    """Verify the inbound session cookie and return a context, or None.

    The raw session id stays inside this call: it is read from the cookie, hashed, and looked up.
    It is never returned, logged, or echoed into page source.
    """
    raw = portal_cookies.session_id_from_cookie_header(cookie_header)
    if not raw:
        return None
    return portal_auth.context_from_raw_session(conn, raw)


def session_context_from_cookies(
    conn: sqlite3.Connection,
    cookies: dict[str, str] | None,
) -> Optional[portal_sessions.PortalSessionContext]:
    """Same as `session_context_from_cookie_header` but from a parsed cookie dict."""
    if not cookies:
        return None
    raw = cookies.get(portal_cookies.SESSION_COOKIE_NAME)
    if not raw:
        return None
    return portal_auth.context_from_raw_session(conn, raw)

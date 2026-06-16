"""Cookie builder/parser helpers for the portal HTTP boundary (Phase 8C).

These are pure string helpers — no live HTTP, no socket, no server. They let the future HTTP
adapter (and tests) build hardened `Set-Cookie` values and parse inbound `Cookie` headers without
binding a port. Raw session ids are treated as opaque secrets: this module never logs them and
the access-log sanitizer redacts any cookie header.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from . import portal_sessions, timezone as _tz

# Re-export the canonical session cookie name so callers have one source of truth.
SESSION_COOKIE_NAME = portal_sessions.COOKIE_NAME

_VALID_SAME_SITE = {"Lax", "Strict", "None"}


@dataclass(frozen=True)
class CookieSpec:
    name: str
    value: str
    max_age: Optional[int] = None
    expires: Optional[datetime] = None
    same_site: str = "Lax"
    secure: bool = True
    http_only: bool = True
    path: str = "/"


def parse_cookie_header(header: str | None) -> dict[str, str]:
    """Parse a `Cookie:` request header into a name->value dict.

    Tolerant of stray whitespace and empty segments. Values are returned verbatim (portal
    session ids are URL-safe), so no percent-decoding is attempted. Last value wins on
    duplicate names, matching browser/server convention.
    """
    out: dict[str, str] = {}
    if not header:
        return out
    for segment in header.split(";"):
        segment = segment.strip()
        if not segment or "=" not in segment:
            continue
        name, _, value = segment.partition("=")
        name = name.strip()
        if name:
            out[name] = value.strip()
    return out


def build_set_cookie(spec: CookieSpec) -> str:
    """Render a hardened `Set-Cookie` header value from a CookieSpec."""
    same = spec.same_site if spec.same_site in _VALID_SAME_SITE else "Lax"
    # SameSite=None is only meaningful alongside Secure; enforce it defensively.
    secure = bool(spec.secure) or same == "None"
    parts = [f"{spec.name}={spec.value}", f"Path={spec.path}", f"SameSite={same}"]
    if spec.http_only:
        parts.append("HttpOnly")
    if secure:
        parts.append("Secure")
    if spec.max_age is not None:
        parts.append(f"Max-Age={int(spec.max_age)}")
    if spec.expires is not None:
        # RFC 7231 IMF-fixdate is always GMT; convert the aware datetime to UTC first.
        parts.append("Expires=" + spec.expires.astimezone(_tz.ZoneInfo("UTC")).strftime("%a, %d %b %Y %H:%M:%S GMT"))
    return "; ".join(parts)


def build_session_set_cookie(
    raw_session_id: str,
    *,
    max_age: int | None = 7200,
    same_site: str = "Lax",
    secure: bool = True,
) -> str:
    """Build the hardened session `Set-Cookie` value.

    The raw session id is placed in the cookie value (that is its only legitimate home) and must
    never be logged or written to page source. Attributes are always HttpOnly + Secure + SameSite
    + Path=/ so the cookie cannot be read by JS or sent cross-site over plain HTTP.
    """
    return build_set_cookie(CookieSpec(
        name=SESSION_COOKIE_NAME,
        value=raw_session_id,
        max_age=max_age,
        same_site=same_site,
        secure=secure,
        http_only=True,
        path="/",
    ))


def build_clear_session_cookie() -> str:
    """Build a `Set-Cookie` that expires the session cookie (logout/revoke)."""
    return build_set_cookie(CookieSpec(
        name=SESSION_COOKIE_NAME, value="", max_age=0, same_site="Lax", secure=True, http_only=True, path="/"
    ))


def session_id_from_cookie_header(header: str | None) -> Optional[str]:
    """Extract the raw session id from a Cookie header, or None if absent."""
    return parse_cookie_header(header).get(SESSION_COOKIE_NAME) or None

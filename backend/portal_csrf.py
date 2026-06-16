"""CSRF token foundation for future portal forms (Phase 8C).

Phase 8C exposes only GET render routes, so no live form yet posts. This module is the
stateless, hash-backed foundation that future POST routes (login, plan selection, payment
confirmation) MUST use before mutating state.

Design: a signed, self-contained token `nonce.exp.sig` where `sig = HMAC-SHA256(key, "nonce.exp")`.
Verification recomputes the signature in constant time and rejects expired or tampered tokens.
No raw token is ever persisted or logged; only the per-process signing key (kept in memory) is
secret. Expiry is stamped from the MMT clock helper so the whole project shares one notion of now.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from . import timezone as _tz

KEY_BYTES = 32
NONCE_BYTES = 16
DEFAULT_TTL_SECONDS = 3600


def new_signing_key() -> bytes:
    """Return a fresh in-memory signing key. Never persist or log this value."""
    return secrets.token_bytes(KEY_BYTES)


def _now_epoch(now: datetime | None) -> int:
    base = _tz.to_mmt(now) if now is not None else _tz.now_mmt()
    return int(base.timestamp())


def _sign(key: bytes, payload: str) -> str:
    return hmac.new(key, payload.encode("utf-8"), hashlib.sha256).hexdigest()


@dataclass(frozen=True)
class CsrfVerification:
    valid: bool
    reason: str


def issue_token(key: bytes, *, ttl_seconds: int = DEFAULT_TTL_SECONDS, now: datetime | None = None) -> str:
    """Mint a signed CSRF token bound to an expiry. Hand to a form; never log it."""
    nonce = secrets.token_urlsafe(NONCE_BYTES)
    exp = _now_epoch(now) + int(ttl_seconds)
    payload = f"{nonce}.{exp}"
    return f"{payload}.{_sign(key, payload)}"


def verify_token(key: bytes, token: str | None, *, now: datetime | None = None) -> CsrfVerification:
    """Constant-time verify a CSRF token's signature and expiry."""
    if not token:
        return CsrfVerification(False, "absent")
    parts = token.split(".")
    if len(parts) != 3:
        return CsrfVerification(False, "malformed")
    nonce, exp_str, sig = parts
    payload = f"{nonce}.{exp_str}"
    expected = _sign(key, payload)
    if not hmac.compare_digest(expected, sig or ""):
        return CsrfVerification(False, "bad_signature")
    try:
        exp = int(exp_str)
    except ValueError:
        return CsrfVerification(False, "malformed")
    if exp <= _now_epoch(now):
        return CsrfVerification(False, "expired")
    return CsrfVerification(True, "valid")


def redact(token: str | None) -> str:
    """Non-reversible marker for logs/tests; never emits the raw token."""
    if not token:
        return "csrf:<absent>"
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()[:8]
    return f"csrf:<redacted:{digest}>"

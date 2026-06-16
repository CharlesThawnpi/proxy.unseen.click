"""Hash-only portal token helpers for Phase 8B.

Raw portal tokens/session ids are generated with secure randomness and should exist only in
memory for immediate handoff. DB rows store only SHA-256 handles.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets

TOKEN_BYTES = 32


def generate_opaque_token() -> str:
    """Return a URL-safe opaque token with ~256 bits of randomness."""
    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_token(raw_token: str) -> str:
    return hashlib.sha256((raw_token or "").encode("utf-8")).hexdigest()


def constant_time_equal(left: str, right: str) -> bool:
    return hmac.compare_digest(left or "", right or "")


def verify_token_hash(raw_token: str, stored_hash: str) -> bool:
    return constant_time_equal(hash_token(raw_token), stored_hash)


def fingerprint(raw_token: str) -> str:
    """Short non-secret fingerprint for logs/tests; never reversible."""
    return f"tok:{hash_token(raw_token)[:12]}"


def redact(value: str | None) -> str:
    if not value:
        return "token:<absent>"
    return f"token:<redacted:{hash_token(value)[:8]}>"


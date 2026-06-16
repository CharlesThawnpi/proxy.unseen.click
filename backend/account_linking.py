"""Account-linking short codes — cross-platform profile linking (§9.3, docs/ACCOUNT_LINKING.md).

A customer already on one platform issues a short code; entering it on another platform links
that platform account to the same canonical customer. No email, no password.

Secret-safety rules enforced here:
  - The **raw code is returned exactly once** by `issue_link_code` and is NEVER stored or logged.
    Only its SHA-256 hash lands in `account_link_tokens.code_hash`.
  - Validation is **reason-opaque**: unknown / expired / consumed all yield the same negative
    result with no reason field — no information leak to a code-guesser.
  - Codes are 6–8 chars from an unambiguous alphabet, one-time, and expire in 24h.

Merge note (this slice): when the entered code's customer differs from a customer that already
owns the target platform account, a full profile merge is required. That is intentionally a
**dry-run placeholder** here (no rows mutated) — see `consume_link_code` and the TODO.
"""
from __future__ import annotations

import hashlib
import secrets
import sqlite3
from dataclasses import dataclass
from typing import Optional, Tuple

from . import db as _db
from .account_service import resolve_customer, _validate_platform

# Unambiguous alphabet: no 0/O/1/I/L — easier to read aloud / type for non-technical users.
_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
_CODE_LEN = 8                       # within the 6–8 char rule
_EXPIRY_SECONDS = 24 * 60 * 60      # 24h, one-time


def _hash_code(raw_code: str) -> str:
    """SHA-256 of the normalized (upper, stripped) code. The raw code is never stored."""
    return hashlib.sha256(raw_code.strip().upper().encode("utf-8")).hexdigest()


def _generate_code() -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(_CODE_LEN))


@dataclass(frozen=True)
class LinkValidation:
    """Reason-opaque validation result. On failure, `customer_id` is None and there is
    deliberately NO field explaining why (unknown vs expired vs used are indistinguishable)."""
    valid: bool
    customer_id: Optional[int] = None


@dataclass(frozen=True)
class LinkConsumeResult:
    """Outcome of consuming a code against a target platform account.

    status:
      - "linked"                 → target platform account attached to the issuer's customer.
      - "already_linked"         → target already maps to the issuer's customer (idempotent no-op).
      - "merge_required_dry_run" → target belongs to a DIFFERENT customer; NOT mutated this slice.
      - "invalid"                → reason-opaque code failure (no mutation, code not consumed).
    """
    status: str
    customer_id: Optional[int] = None


def issue_link_code(conn: sqlite3.Connection, customer_id: int) -> str:
    """Issue a fresh one-time link code for `customer_id`. Returns the RAW code (caller must
    show it once and never persist/log it). Only the hash is stored, with a 24h expiry."""
    # Loop guards the (astronomically unlikely) hash collision on the UNIQUE code_hash column.
    for _ in range(8):
        raw = _generate_code()
        code_hash = _hash_code(raw)
        try:
            with _db.transaction(conn):
                conn.execute(
                    "INSERT INTO account_link_tokens(customer_id, code_hash, expires_at) "
                    "VALUES (?,?, datetime('now', ?))",
                    (customer_id, code_hash, f"+{_EXPIRY_SECONDS} seconds"),
                )
            return raw
        except sqlite3.IntegrityError:
            continue
    raise RuntimeError("could not allocate a unique link code")  # never includes a code


def validate_link_code(conn: sqlite3.Connection, code: str) -> LinkValidation:
    """Reason-opaque check: returns the issuer customer_id iff the code is known, unexpired,
    and unconsumed. Every failure path returns the same negative result."""
    code_hash = _hash_code(code)
    row = conn.execute(
        "SELECT customer_id FROM account_link_tokens "
        "WHERE code_hash=? AND consumed_at IS NULL AND expires_at > datetime('now')",
        (code_hash,),
    ).fetchone()
    if not row:
        return LinkValidation(valid=False)
    return LinkValidation(valid=True, customer_id=int(row[0]))


def consume_link_code(conn: sqlite3.Connection, code: str,
                      target_platform_account: Tuple[str, str]) -> LinkConsumeResult:
    """Consume a one-time code, linking `target_platform_account` to the issuer's customer.

    `target_platform_account` is (platform_name, platform_user_id).

    Idempotency / safety:
      - target not yet known        → attach it to the issuer's customer; mark code consumed.
      - target already → issuer      → already-linked no-op; mark code consumed.
      - target → a DIFFERENT customer → MERGE territory. This slice does NOT mutate anything
        (no re-point, no delete, no merged_into) and does NOT consume the code; it returns
        "merge_required_dry_run". TODO(Phase 5+): implement the gated, audited, reversible
        merge (older customer canonical; re-point financial rows; record customer_merges).
    """
    platform_name, platform_user_id = target_platform_account
    _validate_platform(platform_name)
    platform_user_id = str(platform_user_id)
    code_hash = _hash_code(code)

    with _db.transaction(conn):
        # Re-validate inside the transaction (atomic with the consume) to avoid a TOCTOU race.
        row = conn.execute(
            "SELECT id, customer_id FROM account_link_tokens "
            "WHERE code_hash=? AND consumed_at IS NULL AND expires_at > datetime('now')",
            (code_hash,),
        ).fetchone()
        if not row:
            return LinkConsumeResult(status="invalid")
        token_id, issuer_customer_id = int(row[0]), int(row[1])

        existing = conn.execute(
            "SELECT customer_id FROM platform_accounts "
            "WHERE platform_name=? AND platform_user_id=?",
            (platform_name, platform_user_id),
        ).fetchone()

        if existing is None:
            conn.execute(
                "INSERT INTO platform_accounts(platform_name, platform_user_id, customer_id) "
                "VALUES (?,?,?)",
                (platform_name, platform_user_id, issuer_customer_id),
            )
            conn.execute(
                "UPDATE account_link_tokens SET consumed_at=datetime('now') WHERE id=?",
                (token_id,),
            )
            return LinkConsumeResult(status="linked", customer_id=issuer_customer_id)

        if int(existing[0]) == issuer_customer_id:
            # Already the same profile — friendly idempotent no-op. Burn the code anyway
            # (it has served its purpose) so it cannot be reused.
            conn.execute(
                "UPDATE account_link_tokens SET consumed_at=datetime('now') WHERE id=?",
                (token_id,),
            )
            return LinkConsumeResult(status="already_linked", customer_id=issuer_customer_id)

        # Different customer → real merge required. DRY-RUN: mutate nothing, do not consume.
        return LinkConsumeResult(status="merge_required_dry_run", customer_id=issuer_customer_id)

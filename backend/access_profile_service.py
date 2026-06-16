"""AccessProfileService — per-customer access profile placeholder (dry-run; §30A, SECURITY).

In dry-run we create/reuse an `access_profiles` row that stores **only a placeholder token
hash** — never a raw subscription token, never a subscription URL, and (in dry-run) no Hiddify
UUID. In the live phase this placeholder is replaced by the real per-customer token hash +
engine UUID, encrypted-at-rest elsewhere. The placeholder pre-image is explicitly marked so it
can never be mistaken for a real token.
"""
from __future__ import annotations

import hashlib
import secrets
import sqlite3
from dataclasses import dataclass
from typing import Optional

from . import db as _db
from .audit import audit_row


@dataclass(frozen=True)
class AccessProfileResult:
    access_profile_id: int
    reused: bool


def _placeholder_token_hash(customer_id: int) -> str:
    """A 64-hex placeholder hash. Pre-image is clearly labelled 'dryrun-placeholder' so it is
    never a real subscription token; the raw pre-image is not stored."""
    nonce = secrets.token_hex(8)
    pre = f"dryrun-placeholder:cust={customer_id}:{nonce}"
    return hashlib.sha256(pre.encode("utf-8")).hexdigest()


def create_or_reuse(conn: sqlite3.Connection, customer_id: int) -> AccessProfileResult:
    """Reuse the customer's existing non-revoked access profile, else create a placeholder one.
    Stores no raw token/URL and no Hiddify UUID (dry-run). Runs in one transaction."""
    existing = conn.execute(
        "SELECT id FROM access_profiles WHERE customer_id=? AND revoked_at IS NULL ORDER BY id LIMIT 1",
        (customer_id,),
    ).fetchone()
    if existing:
        return AccessProfileResult(access_profile_id=int(existing[0]), reused=True)

    with _db.transaction(conn):
        cur = conn.execute(
            "INSERT INTO access_profiles(customer_id, token_sha256, token_storage_version, hiddify_uuid) "
            "VALUES (?,?,?,NULL)",
            (customer_id, _placeholder_token_hash(customer_id), 1),
        )
        apid = int(cur.lastrowid)
        audit_row(conn, "access_profile_placeholder_created", f"access_profile:{apid}",
                  f"customer:{customer_id} (dry-run placeholder; no raw token/URL/UUID)")
    return AccessProfileResult(access_profile_id=apid, reused=False)

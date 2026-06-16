"""Future portal auth boundary.

Phase 8 intentionally has no real customer login. Future work should issue short-lived,
hashed/rotatable portal access handles from an already-linked customer account, resolve them
server-side, and continue displaying `customers.public_customer_code` as the primary identity.
"""
from __future__ import annotations


class PortalAuthNotImplemented(RuntimeError):
    pass


def require_future_auth() -> None:
    """Placeholder guard for future HTTP integration."""
    raise PortalAuthNotImplemented("portal auth is not implemented in Phase 8")


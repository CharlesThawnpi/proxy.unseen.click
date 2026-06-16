"""DeliveryPayload — safe, reference-only model for a subscription delivery (§16, SECURITY).

A DeliveryPayload carries ONLY safe references/metadata:
  - customer_id / subscription_id / access_profile_id (internal ids — not secrets)
  - channel + template_key (payload_ref) — never a raw link
  - mode availability flags (deep_link / copy_link / qr) + the chosen primary_mode
  - branded_token_sha256 — a HASH/handle of the opaque branded token (raw token NEVER kept here)

There is no field for a raw subscription/proxy link, deep-link payload, or QR payload. The raw
branded link is assembled in memory at send time (link_renderer) and is never stored on this
object, in the DB, or in logs.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional

# Delivery mode priority: Hiddify App deep link first, then copy-link, then QR.
MODE_DEEP_LINK = "deep_link"
MODE_COPY_LINK = "copy_link"
MODE_QR = "qr"


@dataclass(frozen=True)
class DeliveryPayload:
    customer_id: int
    subscription_id: Optional[int]
    access_profile_id: Optional[int]
    channel: str                      # telegram|messenger|viber|whatsapp
    template_key: str                 # payload_ref, e.g. "delivery:sub:7" — never a raw link
    deep_link_available: bool
    copy_link_available: bool
    qr_available: bool
    primary_mode: str                 # MODE_DEEP_LINK|MODE_COPY_LINK|MODE_QR
    branded_token_sha256: Optional[str] = None   # hash/handle only; raw token never stored

    @staticmethod
    def choose_primary_mode(deep: bool, copy: bool, qr: bool) -> str:
        if deep:
            return MODE_DEEP_LINK
        if copy:
            return MODE_COPY_LINK
        if qr:
            return MODE_QR
        return MODE_COPY_LINK   # safe default; copy-link of the branded link always derivable

    def audit_detail(self) -> str:
        """Sanitized one-line detail for audit — refs/flags only, NO link/token/QR."""
        return (f"customer:{self.customer_id} sub:{self.subscription_id} "
                f"ap:{self.access_profile_id} channel:{self.channel} mode:{self.primary_mode} "
                f"deep:{int(self.deep_link_available)} copy:{int(self.copy_link_available)} "
                f"qr:{int(self.qr_available)} tmpl:{self.template_key}")

    def as_dict(self) -> dict:
        return asdict(self)

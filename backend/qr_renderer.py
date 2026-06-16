"""QR rendering — PLANNED, not generated in Phase 6 (honest capability reporting).

The project is **stdlib-only** on the control plane; a real QR encoder would require a
third-party dependency (e.g. `qrcode`/`Pillow`), which is out of scope and a risky add. So QR
is **not generated** here. This module honestly reports QR as a *planned/manual* fallback and
provides a sanitized plan descriptor — it never produces or persists a QR payload.

When QR is implemented later, it MUST be generated **in memory from the branded link at
send time** and **never persisted or logged** (the QR encodes the secret link).
"""
from __future__ import annotations

from dataclasses import dataclass

# Phase 6: no safe stdlib QR encoder is available without adding a dependency → not generated.
QR_IMPLEMENTED = False


@dataclass(frozen=True)
class QrPlan:
    available: bool          # False in Phase 6 (planned, not generated)
    status: str              # "planned" | "generated"
    note: str


def qr_plan() -> QrPlan:
    """Honest QR capability for delivery. Phase 6: planned (no payload produced/persisted)."""
    if QR_IMPLEMENTED:  # pragma: no cover - reserved for the future implemented path
        return QrPlan(available=True, status="generated",
                      note="QR generated in memory from the branded link at send time; never persisted")
    return QrPlan(available=False, status="planned",
                  note="QR not generated in Phase 6 (stdlib-only; no safe encoder). Manual/planned "
                       "fallback — deep-link + copy-link cover delivery for now.")

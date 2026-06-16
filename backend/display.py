"""Profile display rules (computed, not stored).

The "Fast" display rule: if a plan entitles only ONE fast tier, show it as "Fast";
if it entitles BOTH fast tiers, show "Fast1" and "Fast2". "Secure" is always "Secure".
Computed from entitlements at render time, never stored as a label.
"""
from __future__ import annotations


def fast_labels(profile_codes: list[str]) -> dict[str, str]:
    """Map entitled profile_codes -> display label per the Fast rule.

    profile_codes is a subset of {"FAST1","FAST2","SECURE"}.
    """
    codes = set(profile_codes)
    fast = [c for c in ("FAST1", "FAST2") if c in codes]
    out: dict[str, str] = {}
    if len(fast) == 1:
        out[fast[0]] = "Fast"
    else:
        for c in fast:
            out[c] = "Fast1" if c == "FAST1" else "Fast2"
    if "SECURE" in codes:
        out["SECURE"] = "Secure"
    return out

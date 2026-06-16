"""Plan → region/protocol entitlement resolver — DB-driven, no hardcoded plan values (§7, §6).

"Entitlement" = the plan is *allowed* to use a region/protocol (a contractual fact from
`plan_region_entitlements` / `plan_protocol_entitlements`). It is distinct from *availability*
(whether a usable node/protocol exists right now — see `availability.py`).

Product rules are preserved but enforced via DB rows, not constants:
  - DE is the default/entry region (`proxy_regions.is_default`).
  - SG is premium-only (`proxy_regions.is_premium_only`) and only PRO/MAX are entitled to it (seed).
  - FAST1=Hysteria2, FAST2=Shadowsocks, Secure=VLESS-Reality (`protocol_profiles.engine_protocol`).
  - FAST display rule: one fast tier → "Fast"; both → "Fast1"/"Fast2" (see `display.fast_labels`).
An unknown or disabled plan returns a safe error object — it never crashes.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

from . import display, seed


class UnknownPlanError(ValueError):
    pass


class DisabledPlanError(ValueError):
    pass


@dataclass(frozen=True)
class Entitlements:
    plan_code: str
    display_name: str
    regions: List[str]                      # entitled region codes (e.g. de, us, sg)
    profiles: List[str]                     # entitled profile codes (FAST1/FAST2/SECURE)
    profile_labels: Dict[str, str]          # FAST display rule applied
    default_region: Optional[str]           # the entry region (DE), if entitled
    premium_regions: List[str] = field(default_factory=list)   # entitled & premium-only (e.g. sg)

    def is_region_entitled(self, region_code: str) -> bool:
        return region_code in self.regions

    def is_protocol_entitled(self, profile_code: str) -> bool:
        return profile_code in self.profiles

    def as_dict(self) -> dict:
        return asdict(self)


def _plan_row(conn: sqlite3.Connection, plan_code: str):
    row = conn.execute("SELECT * FROM plans WHERE plan_code=?", (plan_code,)).fetchone()
    if row is None:
        raise UnknownPlanError("unknown plan_code")   # value not echoed
    if "is_enabled" in row.keys() and int(row["is_enabled"]) == 0:
        raise DisabledPlanError("plan is disabled")
    return row


def resolve(conn: sqlite3.Connection, plan_code: str) -> Entitlements:
    """Resolve a plan's entitlements purely from DB rows. Raises Unknown/DisabledPlanError safely."""
    p = _plan_row(conn, plan_code)
    regions = seed.entitled_regions(conn, plan_code)
    profiles = seed.entitled_profiles(conn, plan_code)
    labels = display.fast_labels(profiles)

    default_region = None
    premium: List[str] = []
    if regions:
        placeholders = ",".join("?" * len(regions))
        drow = conn.execute(
            f"SELECT region_code FROM proxy_regions WHERE is_default=1 AND region_code IN ({placeholders})",
            regions).fetchone()
        default_region = drow[0] if drow else None
        premium = [r[0] for r in conn.execute(
            f"SELECT region_code FROM proxy_regions "
            f"WHERE is_premium_only=1 AND region_code IN ({placeholders}) ORDER BY region_code",
            regions).fetchall()]

    return Entitlements(
        plan_code=p["plan_code"], display_name=p["display_name_en"], regions=regions,
        profiles=profiles, profile_labels=labels, default_region=default_region,
        premium_regions=premium)

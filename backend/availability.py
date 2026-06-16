"""Customer availability resolver — entitlement × node resilience (§6.2, §7).

Combines `entitlements` (what a plan is *allowed* to use) with `node_resilience` (what is
*usable* right now) into an honest per-region / per-protocol availability picture, with graceful
degradation:

  - A region is **available** (for a mode) iff it is entitled AND has ≥1 candidate node in that
    mode that is not down. Otherwise it is **unavailable** with sanitized reasons.
  - A protocol is **available in a region** iff entitled AND some candidate node there has it up.
  - A down node is dropped; remaining nodes keep serving. If ALL nodes in a region are down/
    unavailable → that region is unavailable (we do NOT silently substitute another region).
  - SG unavailability never affects BASIC/CORE (they aren't entitled to SG).

Modes: "dry_run" (test/standby/live candidates) and "live" (only live-ready nodes). Everything
returned is sanitized — region/protocol codes, statuses, counts, reason codes; no IP/secret.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field, asdict
from typing import Dict, List

from . import entitlements as _ent, node_resilience as _nr

MODE_DRY_RUN = "dry_run"
MODE_LIVE = "live"


@dataclass(frozen=True)
class ProtocolAvailability:
    profile_code: str
    label: str
    entitled: bool
    available: bool
    reasons: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class RegionAvailability:
    region_code: str
    entitled: bool
    available: bool
    is_premium_only: bool
    candidate_nodes: List[str] = field(default_factory=list)   # node codes (not secrets)
    protocols: List[ProtocolAvailability] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class CustomerAvailability:
    plan_code: str
    mode: str
    entitled_regions: List[str]
    entitled_protocols: List[str]
    available_regions: List[str]
    unavailable_regions: List[dict]                 # [{region, reasons}]
    regions: Dict[str, dict] = field(default_factory=dict)   # region_code -> RegionAvailability dict

    def as_dict(self) -> dict:
        return asdict(self)


def _candidate(readiness: _nr.NodeReadiness, mode: str) -> bool:
    return readiness.live_ready if mode == MODE_LIVE else readiness.dry_run_candidate


def resolve(conn: sqlite3.Connection, plan_code: str, mode: str = MODE_DRY_RUN) -> CustomerAvailability:
    """Resolve availability for a plan in the given mode. Raises Unknown/DisabledPlanError safely
    (via entitlements.resolve)."""
    ent = _ent.resolve(conn, plan_code)
    readiness_all = _nr.readiness_for_regions(conn, ent.regions)
    by_region: Dict[str, List[_nr.NodeReadiness]] = {}
    for r in readiness_all:
        by_region.setdefault(r.region_code, []).append(r)

    regions_out: Dict[str, dict] = {}
    available_regions: List[str] = []
    unavailable_regions: List[dict] = []

    for region in ent.regions:
        prow = conn.execute(
            "SELECT is_premium_only FROM proxy_regions WHERE region_code=?", (region,)).fetchone()
        premium = bool(prow[0]) if prow else False
        readinesses = by_region.get(region, [])
        candidates = [r for r in readinesses if _candidate(r, mode)]
        region_reasons: List[str] = []

        if not readinesses:
            region_reasons.append(_nr.NO_CANDIDATE_NODE)
        elif not candidates:
            # No usable node in this mode — surface the (deduped) reasons from the region's nodes.
            if all(r.health == _nr.HEALTH_DOWN for r in readinesses):
                region_reasons.append(_nr.NODE_DOWN)
            for r in readinesses:
                for reason in r.reasons:
                    if reason not in region_reasons:
                        region_reasons.append(reason)
            if not region_reasons:
                region_reasons.append(_nr.NO_CANDIDATE_NODE)

        # Protocol availability within this region (only meaningful if there are candidates).
        protocols_out: List[ProtocolAvailability] = []
        for code in ("FAST1", "FAST2", "SECURE"):
            entitled = ent.is_protocol_entitled(code)
            if not entitled:
                continue
            label = ent.profile_labels.get(code, code)
            avail = any(_nr.node_protocol_available(conn, r.node_code, code) for r in candidates)
            preasons: List[str] = []
            if not candidates:
                preasons.append(_nr.NO_CANDIDATE_NODE)
            elif not avail:
                preasons.append(_nr.PROTOCOL_MISSING)
            protocols_out.append(ProtocolAvailability(
                profile_code=code, label=label, entitled=True, available=bool(candidates) and avail,
                reasons=preasons))

        region_available = bool(candidates)
        ra = RegionAvailability(
            region_code=region, entitled=True, available=region_available, is_premium_only=premium,
            candidate_nodes=[r.node_code for r in candidates], protocols=protocols_out,
            reasons=region_reasons)
        regions_out[region] = asdict(ra)
        if region_available:
            available_regions.append(region)
        else:
            unavailable_regions.append({"region": region, "reasons": region_reasons})

    return CustomerAvailability(
        plan_code=ent.plan_code, mode=mode, entitled_regions=ent.regions,
        entitled_protocols=ent.profiles, available_regions=available_regions,
        unavailable_regions=unavailable_regions, regions=regions_out)

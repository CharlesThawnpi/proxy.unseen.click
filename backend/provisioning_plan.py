"""Provisioning plan builder — pure planning, no DB writes, no network (§6, §8).

Resolves a plan_code into the sanitized intent needed to provision a subscription:
entitled regions/protocols (from DB rows, never hardcoded), quota (GiB → Hiddify GB),
duration, candidate nodes by region/status, and the **blocking reasons** that forbid a live
mutation. It also builds the **sanitized intended Hiddify API call summary** — the GiB→GB
conversion is applied deliberately here, and the summary never contains the API key, admin
path, user UUIDs, subscription URLs, proxy links, or QR payloads.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field, asdict
from typing import List, Optional

from . import config, display, seed, units
from .hiddify import HiddifyClient


class UnknownPlanError(ValueError):
    pass


@dataclass(frozen=True)
class NodeCandidate:
    node_code: str
    region_code: str
    status: str            # planned|test|standby|live
    usable_for_dry_run: bool
    usable_for_live: bool


@dataclass(frozen=True)
class ProvisioningPlan:
    plan_code: str
    display_name: str
    quota_gib: int
    quota_gb: float               # Hiddify usage_limit_GB (GiB→GB converted)
    package_days: int
    price_mmk: int
    regions: List[str]
    profiles: List[str]
    profile_labels: dict          # FAST rule applied
    premium_regions: List[str]    # e.g. sg (premium-only)
    candidate_nodes: List[NodeCandidate] = field(default_factory=list)
    live_blockers: List[str] = field(default_factory=list)

    @property
    def live_allowed(self) -> bool:
        return not self.live_blockers

    def sanitized_summary(self) -> dict:
        """Loggable/JSON-able summary — contains NO secrets (no key/path/UUID/links/QR)."""
        d = asdict(self)
        d["candidate_nodes"] = [asdict(n) for n in self.candidate_nodes]
        d["live_allowed"] = self.live_allowed
        return d


def _plan_row(conn: sqlite3.Connection, plan_code: str):
    row = conn.execute("SELECT * FROM plans WHERE plan_code=?", (plan_code,)).fetchone()
    if not row:
        raise UnknownPlanError(f"unknown plan_code")  # value not echoed
    return row


def live_blockers(node: Optional[NodeCandidate]) -> List[str]:
    """The reasons a live provisioning is refused. Empty list would mean live is allowed."""
    reasons: List[str] = []
    if config.PHASE4C_LIVE_PROVISION_DISABLED:
        reasons.append("phase4c_live_disabled")
    if config.LEAKED_KEY_REBUILD_PENDING:
        reasons.append("leaked_key_rebuild_pending")
    if node is None:
        reasons.append("no_candidate_node")
    elif node.status != "live":
        reasons.append(f"node_not_live:{node.status}")
    return reasons


def build_plan(conn: sqlite3.Connection, plan_code: str,
               preferred_node: Optional[str] = None) -> ProvisioningPlan:
    """Resolve a full sanitized provisioning plan for `plan_code` from DB rows."""
    p = _plan_row(conn, plan_code)
    regions = seed.entitled_regions(conn, plan_code)
    profiles = seed.entitled_profiles(conn, plan_code)
    labels = display.fast_labels(profiles)

    premium: List[str] = []
    candidates: List[NodeCandidate] = []
    if regions:
        placeholders = ",".join("?" * len(regions))
        premium = [r[0] for r in conn.execute(
            f"SELECT region_code FROM proxy_regions "
            f"WHERE is_premium_only=1 AND region_code IN ({placeholders}) ORDER BY region_code",
            regions).fetchall()]
        rows = conn.execute(
            f"SELECT node_code, region_code, status FROM proxy_nodes "
            f"WHERE region_code IN ({placeholders}) ORDER BY node_code",
            regions,
        ).fetchall()
        for r in rows:
            status = r["status"]
            candidates.append(NodeCandidate(
                node_code=r["node_code"], region_code=r["region_code"], status=status,
                usable_for_dry_run=True,                 # any seeded node may be planned in dry-run
                usable_for_live=(status == "live"),
            ))

    # choose the node we'd target (preferred if given & present, else first default-region node)
    target = None
    if preferred_node:
        target = next((n for n in candidates if n.node_code == preferred_node), None)
    if target is None:
        target = candidates[0] if candidates else None

    return ProvisioningPlan(
        plan_code=p["plan_code"], display_name=p["display_name_en"],
        quota_gib=int(p["data_limit_gib"]), quota_gb=units.gib_to_gb(p["data_limit_gib"]),
        package_days=int(p["duration_days"]), price_mmk=int(p["price_mmk"]),
        regions=regions, profiles=profiles, profile_labels=labels, premium_regions=premium,
        candidate_nodes=candidates, live_blockers=live_blockers(target),
    )


def hiddify_mutation_plan(plan: ProvisioningPlan, customer_ref: str) -> dict:
    """Sanitized intended Hiddify API call (NOT executed). Mirrors HiddifyClient.create_user's
    payload construction (GiB→GB at the boundary). Contains NO secret: no API key, no admin
    path, no UUID, no subscription URL/proxy link/QR. `customer_ref` is a non-secret label
    (e.g. the public_customer_code), never a UUID/token."""
    return {
        "method": "POST",
        "path": HiddifyClient.user_list_path(),          # "/user/"  (relative; no host/secret path)
        "name": f"unseen-{customer_ref}",                 # display name only
        "usage_limit_GB": plan.quota_gb,                  # GiB→GB converted intentionally
        "package_days": plan.package_days,
        "enable": True,
        "mode": "no_reset",
        "note": "DRY-RUN INTENT ONLY — not sent; live mutation hard-disabled in Phase 4C",
    }

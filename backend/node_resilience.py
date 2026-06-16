"""Node resilience — status, health, readiness reasons, candidate selection (§6.2).

Separates two axes (kept distinct from entitlement):
  - **status** (DB `proxy_nodes.status`): planned | test | standby | live | retired
  - **health** (derived from OPEN `node_alerts`): healthy | degraded (WARN) | down (CRITICAL/DOWN)

From these it computes per-node **readiness** for a mode (dry_run | live) with a sanitized reason
vocabulary, plus candidate selection with graceful degradation (a down node is dropped; other
nodes keep serving). Per-node live blockers are **data-driven** (`node_live_blockers`, e.g. de1's
`leaked_key_rebuild_pending`) — no hardcoded node codes here. No network; no real metrics required.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field, asdict
from typing import List

# ---- readiness / blocking reason vocabulary (sanitized codes; never secrets) ----
NODE_NOT_LIVE = "node_not_live"
NODE_STATUS_TEST = "node_status_test"
NODE_STATUS_PLANNED = "node_status_planned"
NODE_STATUS_STANDBY = "node_status_standby"
NODE_STATUS_RETIRED = "node_status_retired"
NODE_DOWN = "node_down"
NODE_DEGRADED = "node_degraded"
PROTOCOL_MISSING = "protocol_missing"
LEAKED_KEY_REBUILD_PENDING = "leaked_key_rebuild_pending"
NO_CANDIDATE_NODE = "no_candidate_node"
REGION_NOT_ENTITLED = "region_not_entitled"
PROTOCOL_NOT_ENTITLED = "protocol_not_entitled"
PHASE4C_LIVE_DISABLED = "phase4c_live_disabled"

HEALTH_HEALTHY = "healthy"
HEALTH_DEGRADED = "degraded"
HEALTH_DOWN = "down"

_STATUS_REASON = {
    "test": NODE_STATUS_TEST,
    "planned": NODE_STATUS_PLANNED,
    "standby": NODE_STATUS_STANDBY,
    "retired": NODE_STATUS_RETIRED,
}


@dataclass(frozen=True)
class NodeReadiness:
    node_code: str
    region_code: str
    status: str
    health: str
    dry_run_candidate: bool          # usable for a dry-run plan preview
    live_ready: bool                 # usable for a LIVE provisioning right now
    reasons: List[str] = field(default_factory=list)   # why NOT live (sanitized)

    def as_dict(self) -> dict:
        return asdict(self)


def node_health(conn: sqlite3.Connection, node_code: str) -> str:
    """Derive health from OPEN node_alerts (cleared_at IS NULL).

    Policy (Phase 7 health monitor):
      - a **DOWN** alert (reachability: tcp_443/tcp_80/panel) → `down` → node is DROPPED from all
        candidates (no traffic to an unreachable node).
      - a **CRITICAL** or **WARN** alert (resource pressure: cpu/ram/disk, or ssh/management) →
        `degraded`. A degraded node REMAINS a dry-run candidate (previews still show it) but is
        NOT live-ready (we don't route live traffic to a stressed node — `node_degraded` is an open
        reason, so `live_ready` is False).
    """
    rows = conn.execute(
        "SELECT level FROM node_alerts WHERE node_code=? AND cleared_at IS NULL", (node_code,)
    ).fetchall()
    levels = {(r[0] or "").upper() for r in rows}
    if "DOWN" in levels:
        return HEALTH_DOWN
    if "CRITICAL" in levels or "WARN" in levels:
        return HEALTH_DEGRADED
    return HEALTH_HEALTHY


def _live_blockers(conn: sqlite3.Connection, node_code: str) -> List[str]:
    return [r[0] for r in conn.execute(
        "SELECT reason FROM node_live_blockers WHERE node_code=? ORDER BY reason", (node_code,)).fetchall()]


def node_readiness(conn: sqlite3.Connection, node_code: str, region_code: str,
                   status: str) -> NodeReadiness:
    """Compute readiness for one node. Live requires: status=live, healthy/degraded (not down),
    no data-driven live blockers, and the Phase 4C global live gate cleared."""
    health = node_health(conn, node_code)
    reasons: List[str] = []

    # Per-node readiness reflects NODE-INTRINSIC factors only (status/health/data-driven blockers).
    # The GLOBAL phase gate (phase4c_live_disabled) is applied separately at the provisioning layer
    # (provisioning_plan.live_blockers / availability mode), so graceful degradation stays visible.

    # Status axis.
    if status != "live":
        reasons.append(NODE_NOT_LIVE)
        if status in _STATUS_REASON:
            reasons.append(_STATUS_REASON[status])

    # Health axis.
    if health == HEALTH_DOWN:
        reasons.append(NODE_DOWN)
    elif health == HEALTH_DEGRADED:
        reasons.append(NODE_DEGRADED)

    # Data-driven per-node live blockers (e.g. de1 leaked_key_rebuild_pending).
    reasons.extend(_live_blockers(conn, node_code))

    # Dry-run candidate: test/standby/live nodes that are not down (planned/retired excluded).
    dry_run_candidate = status in ("test", "standby", "live") and health != HEALTH_DOWN
    # Live readiness: live + not down + no blockers at all.
    live_ready = (status == "live" and health != HEALTH_DOWN and not reasons)

    # De-dup while preserving order.
    seen, ordered = set(), []
    for r in reasons:
        if r not in seen:
            seen.add(r); ordered.append(r)
    return NodeReadiness(node_code=node_code, region_code=region_code, status=status,
                         health=health, dry_run_candidate=dry_run_candidate,
                         live_ready=live_ready, reasons=ordered)


def nodes_in_regions(conn: sqlite3.Connection, regions: List[str]) -> List[sqlite3.Row]:
    if not regions:
        return []
    placeholders = ",".join("?" * len(regions))
    return conn.execute(
        f"SELECT node_code, region_code, status FROM proxy_nodes "
        f"WHERE region_code IN ({placeholders}) ORDER BY region_code, node_code", regions).fetchall()


def readiness_for_regions(conn: sqlite3.Connection, regions: List[str]) -> List[NodeReadiness]:
    return [node_readiness(conn, r["node_code"], r["region_code"], r["status"])
            for r in nodes_in_regions(conn, regions)]


def node_protocol_available(conn: sqlite3.Connection, node_code: str, profile_code: str) -> bool:
    """Node-specific protocol availability. ABSENCE of a row → available (back-compat default)."""
    row = conn.execute(
        "SELECT is_available FROM proxy_node_protocols WHERE node_code=? AND profile_code=?",
        (node_code, profile_code)).fetchone()
    return True if row is None else bool(row[0])

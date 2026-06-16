"""Alert evaluator — sanitized node_alerts lifecycle from ProbeResults (§30A.3, §6.2).

Maps a sanitized `ProbeResult` to desired alert states and reconciles them against OPEN
`node_alerts` rows idempotently:
  - one OPEN alert per (node, metric); raising again with the SAME level is a no-op (no dup),
  - a level change clears the old and raises the new,
  - a resolved condition CLEARS the open alert (sets cleared_at).

Levels: WARN | CRITICAL | DOWN. Thresholds (warn≈75, critical≈90) are read from `settings`
(`node_alert_warn_pct` / `node_alert_critical_pct`) with safe fallbacks. Alert `metric` is a
sanitized check name (cpu/ram/disk/bandwidth/tcp_443/tcp_80/ssh_22/panel); `value` is a percent
or 0. **No secret/URL/host ever lands in an alert.**
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from . import db as _db, timezone as _tz
from .node_probe import ProbeResult

# ---- levels ----
WARN = "WARN"
CRITICAL = "CRITICAL"
DOWN = "DOWN"

# ---- sanitized reason codes (for ProbeResult.reasons / CLI; not stored in the alert row) ----
TCP_443_DOWN = "tcp_443_down"
TCP_80_DOWN = "tcp_80_down"
SSH_22_DOWN = "ssh_22_down"
PANEL_UNREACHABLE = "panel_unreachable"
HIGH_CPU = "high_cpu"
HIGH_RAM = "high_ram"
HIGH_DISK = "high_disk"
BANDWIDTH_WARN = "bandwidth_warn"
BANDWIDTH_CRITICAL = "bandwidth_critical"
PROBE_TIMEOUT = "probe_timeout"
PROBE_ERROR_SANITIZED = "probe_error_sanitized"
UNKNOWN = "unknown"

_DEFAULT_WARN = 75
_DEFAULT_CRITICAL = 90


def thresholds(conn: sqlite3.Connection) -> Tuple[int, int]:
    """(warn_pct, critical_pct) from settings, with safe fallbacks."""
    def _get(key: str, default: int) -> int:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        try:
            return int(row[0]) if row and row[0] is not None else default
        except (TypeError, ValueError):
            return default
    return _get("node_alert_warn_pct", _DEFAULT_WARN), _get("node_alert_critical_pct", _DEFAULT_CRITICAL)


def _resource_level(pct: Optional[int], warn: int, crit: int) -> Optional[str]:
    if pct is None or pct < 0:
        return None
    if pct >= crit:
        return CRITICAL
    if pct >= warn:
        return WARN
    return None


def desired_alerts(conn: sqlite3.Connection, pr: ProbeResult) -> Dict[str, Tuple[str, float, str]]:
    """Compute desired {metric: (level, value, reason_code)} for a ProbeResult. Reachability
    failures are DOWN; resource pressure is WARN/CRITICAL; SSH down is WARN (management only)."""
    warn, crit = thresholds(conn)
    out: Dict[str, Tuple[str, float, str]] = {}

    # Reachability (customer-facing data plane).
    if pr.tcp_443_ok is False:
        out["tcp_443"] = (DOWN, 0, TCP_443_DOWN)
    if pr.tcp_80_ok is False:
        out["tcp_80"] = (DOWN, 0, TCP_80_DOWN)
    # Panel reachable over public root only; a 5xx / None-after-probe is treated as down.
    if pr.panel_http_status is not None and pr.panel_http_status >= 500:
        out["panel"] = (DOWN, float(pr.panel_http_status), PANEL_UNREACHABLE)
    # SSH is management only → WARN (does not drop a node from customer candidates).
    if pr.tcp_22_ok is False:
        out["ssh_22"] = (WARN, 0, SSH_22_DOWN)

    # Resources.
    for metric, pct, reason in (("cpu", pr.cpu_pct, HIGH_CPU), ("ram", pr.ram_pct, HIGH_RAM),
                                ("disk", pr.disk_pct, HIGH_DISK)):
        lvl = _resource_level(pct, warn, crit)
        if lvl:
            out[metric] = (lvl, float(pct), reason)
    return out


def _open_alerts(conn: sqlite3.Connection, node_code: str) -> Dict[str, sqlite3.Row]:
    rows = conn.execute(
        "SELECT * FROM node_alerts WHERE node_code=? AND cleared_at IS NULL", (node_code,)).fetchall()
    return {r["metric"]: r for r in rows}


@dataclass
class AlertReconcile:
    raised: List[str]
    cleared: List[str]
    kept: List[str]


def evaluate(conn: sqlite3.Connection, pr: ProbeResult) -> AlertReconcile:
    """Reconcile OPEN node_alerts for one node against the ProbeResult. Idempotent (no dup opens)."""
    desired = desired_alerts(conn, pr)
    raised: List[str] = []
    cleared: List[str] = []
    kept: List[str] = []
    with _db.transaction(conn):
        now = _tz.storage_mmt(_tz.now_mmt())
        existing = _open_alerts(conn, pr.node_code)
        # Raise / keep / level-change.
        for metric, (level, value, _reason) in desired.items():
            cur = existing.get(metric)
            if cur is None:
                conn.execute(
                    "INSERT INTO node_alerts(node_code, level, metric, value, raised_at) VALUES (?,?,?,?,?)",
                    (pr.node_code, level, metric, value, now))
                raised.append(f"{metric}:{level}")
            elif cur["level"] == level:
                kept.append(f"{metric}:{level}")           # no duplicate open alert
            else:
                conn.execute("UPDATE node_alerts SET cleared_at=? WHERE id=?", (now, cur["id"]))
                conn.execute(
                    "INSERT INTO node_alerts(node_code, level, metric, value, raised_at) VALUES (?,?,?,?,?)",
                    (pr.node_code, level, metric, value, now))
                raised.append(f"{metric}:{level}")
        # Clear open alerts whose condition resolved.
        for metric, row in existing.items():
            if metric not in desired:
                conn.execute("UPDATE node_alerts SET cleared_at=? WHERE id=?", (now, row["id"]))
                cleared.append(f"{metric}:{row['level']}")
    return AlertReconcile(raised=raised, cleared=cleared, kept=kept)


def open_alert_counts(conn: sqlite3.Connection) -> dict:
    """Sanitized histogram of OPEN alerts by level (for the preview CLI)."""
    return {r[0]: int(r[1]) for r in conn.execute(
        "SELECT level, COUNT(*) FROM node_alerts WHERE cleared_at IS NULL GROUP BY level")}

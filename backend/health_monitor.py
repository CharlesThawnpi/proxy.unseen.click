"""Health monitor — once-only orchestration (NO daemon, NO scheduler, NO systemd).

`monitor_once` probes every node (via an injected `Prober`, mock by default), and — only when
`write=True` — appends a `node_metrics` sample and reconciles `node_alerts`. Default is **dry-run**
(no writes, no network with the mock prober). Returns a sanitized summary (statuses + reason codes
+ alert reconcile counts) — never a raw error, URL, IP, or secret.

This is a single pass invoked by a CLI/test. A real cron/timer is intentionally NOT created here.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from . import alerting, metric_writer
from .node_probe import MockProber, Prober, ProbeResult


@dataclass
class NodeMonitorOutcome:
    node_code: str
    status: str
    reasons: List[str] = field(default_factory=list)
    metric_id: Optional[int] = None
    raised: List[str] = field(default_factory=list)
    cleared: List[str] = field(default_factory=list)


@dataclass
class MonitorSummary:
    write: bool
    nodes: int = 0
    outcomes: List[dict] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"write": self.write, "nodes": self.nodes, "outcomes": self.outcomes}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def monitor_once(conn: sqlite3.Connection, prober: Optional[Prober] = None,
                 write: bool = False) -> MonitorSummary:
    """One monitoring pass over all nodes. write=False (default) = dry-run (no DB writes)."""
    prober = prober or MockProber()
    summary = MonitorSummary(write=write)
    nodes = conn.execute(
        "SELECT node_code, region_code, status, public_hostname, public_ip FROM proxy_nodes "
        "ORDER BY node_code").fetchall()
    for node in nodes:
        pr: ProbeResult = prober.probe(node)
        if not pr.ts:
            pr.ts = _utc_now()
        outcome = NodeMonitorOutcome(node_code=pr.node_code, status=pr.status, reasons=list(pr.reasons))
        if write:
            outcome.metric_id = metric_writer.write_metric(conn, pr)
            rec = alerting.evaluate(conn, pr)
            outcome.raised = rec.raised
            outcome.cleared = rec.cleared
        summary.outcomes.append(outcome.__dict__)
        summary.nodes += 1
    return summary

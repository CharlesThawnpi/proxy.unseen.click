#!/usr/bin/env python3
"""UNSEEN PROXY — Hiddify customer provisioner CLI (Phase 4A: dry-run / audit only).

Default is DRY-RUN. A live Hiddify mutation requires BOTH:
  1. env latch  UNSEENPROXY_HIDDIFY_PROVISION_LIVE_ENABLED=1
  2. flags      --live --confirm
In this phase, live mutations are not performed; without the double gate the tool refuses.

Output is sanitized: node alias / region / quota / expiry / profile names only — never the
API key, admin proxy path, user UUIDs, or subscription/proxy links.
"""
from __future__ import annotations

import argparse
import os
import sys

# make the project importable when run directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import config, customer_code, db as dbmod, display, migrate, seed, units  # noqa: E402
from backend.hiddify import HiddifyClient  # noqa: E402


def _open(db_path: str):
    return dbmod.connect(db_path)


def _live_allowed(args) -> bool:
    return config.live_latch_enabled() and getattr(args, "live", False) and getattr(args, "confirm", False)


def cmd_audit(args) -> int:
    if not os.path.exists(args.db):
        print(f"[audit] DB not found at {args.db} (run migrate first). DRY/READONLY.")
        return 0
    conn = _open(args.db)
    applied = [r[0] for r in conn.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()] \
        if conn.execute("SELECT name FROM sqlite_master WHERE name='schema_migrations'").fetchone() else []
    print("[audit] migrations applied:", applied or "(none)")
    print("[audit] integrity_check:", "ok" if dbmod.integrity_ok(conn) else "FAILED")
    print("[audit] foreign_key violations:", len(dbmod.foreign_key_violations(conn)))
    for t in ("plans", "proxy_regions", "protocol_profiles", "proxy_nodes"):
        n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"[audit] {t}: {n} rows")
    print("[audit] live latch:", "ENABLED" if config.live_latch_enabled() else "disabled (safe)")
    conn.close()
    return 0


def cmd_status(args) -> int:
    """DB-only node status (no network). Sanitized."""
    conn = _open(args.db)
    rows = conn.execute(
        "SELECT node_code,region_code,status,verification_status,det_os,is_master_colocated "
        "FROM proxy_nodes ORDER BY node_code").fetchall()
    if not rows:
        print("[status] no nodes seeded.")
    for r in rows:
        print(f"[status] node={r['node_code']} region={r['region_code']} status={r['status']} "
              f"verify={r['verification_status']} os={r['det_os'] or '?'} colocated={r['is_master_colocated']}")
    print("[status] (DB-only; no Hiddify network calls in this phase)")
    conn.close()
    return 0


def cmd_validate_contract(args) -> int:
    """Confirm the client's path builders match the verified contract (no network)."""
    checks = {
        "user list path": HiddifyClient.user_list_path() == "/user/",
        "user path": HiddifyClient.user_path("UUID").endswith("/user/UUID/"),
        "all-configs path": HiddifyClient.all_configs_path("UUID").startswith("/all-configs/?uuid="),
        "GiB->GB(10)=10.74": units.gib_to_gb(10) == 10.74,
        "auth header name": "Hiddify-API-Key",  # documented; asserted in tests
    }
    ok = all(v for k, v in checks.items() if isinstance(v, bool))
    for k, v in checks.items():
        print(f"[contract] {k}: {v}")
    print("[contract] RESULT:", "OK" if ok else "MISMATCH")
    return 0 if ok else 1


def _plan_preview(conn, plan_code: str):
    p = conn.execute("SELECT * FROM plans WHERE plan_code=?", (plan_code,)).fetchone()
    if not p:
        return None
    regions = seed.entitled_regions(conn, plan_code)
    profiles = seed.entitled_profiles(conn, plan_code)
    labels = display.fast_labels(profiles)
    return p, regions, profiles, labels


def cmd_provision_one(args) -> int:
    conn = _open(args.db)
    prev = _plan_preview(conn, args.plan)
    if not prev:
        print(f"[provision] unknown plan '{args.plan}'"); conn.close(); return 1
    p, regions, profiles, labels = prev
    node = conn.execute("SELECT node_code,region_code,status FROM proxy_nodes WHERE node_code=?",
                        (args.node,)).fetchone()
    gib = p["data_limit_gib"]
    print("[provision] DRY-RUN preview (no Hiddify call):")
    print(f"  customer    : {args.customer} (code would be {customer_code.assign_code_for_id(args.customer)})")
    print(f"  plan        : {p['plan_code']} ({p['display_name_en']})")
    print(f"  quota       : {gib} GiB  -> Hiddify usage_limit_GB={units.gib_to_gb(gib)}")
    print(f"  package_days: {p['duration_days']}")
    print(f"  regions     : {','.join(regions)}")
    print(f"  profiles    : {', '.join(f'{c}={labels.get(c, c)}' for c in profiles)}")
    print(f"  node        : {args.node} (status={node['status'] if node else '?'})")
    if node and node["status"] != "live":
        print(f"  NOTE        : node '{args.node}' is status={node['status']} — not live; refusing any live action.")
    if args.live or args.confirm:
        if _live_allowed(args):
            print("  LIVE GATE   : latch+flags present, but Phase 4A performs NO live mutations. Refusing.")
        else:
            print(f"  LIVE GATE   : REFUSED — need env {config.LIVE_ENV_LATCH}=1 AND --live --confirm (and not in Phase 4A).")
    conn.close()
    return 0


def cmd_suspend_one(args) -> int:
    print("[suspend] DRY-RUN: would DISABLE (not delete) the customer's Hiddify user (reversible).")
    print(f"  customer: {args.customer}  node: {args.node}")
    if not _live_allowed(args):
        print(f"  LIVE GATE: REFUSED — need {config.LIVE_ENV_LATCH}=1 AND --live --confirm. (Phase 4A: no live actions.)")
    return 0


def cmd_reconcile_usage(args) -> int:
    print("[reconcile] DRY-RUN: would read current_usage_GB per node and reconcile to GiB (no writes).")
    print("  (Phase 4A: no network; reconciliation logic lands with the sweeper in a later phase.)")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="hiddify_customer_provisioner",
                                 description="UNSEEN PROXY provisioner (dry-run/audit; live double-gated).")
    ap.add_argument("--db", default=config.db_path())
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("audit").set_defaults(func=cmd_audit)
    sub.add_parser("status").set_defaults(func=cmd_status)
    sub.add_parser("validate-contract").set_defaults(func=cmd_validate_contract)

    for name, func in (("provision-one", cmd_provision_one), ("suspend-one", cmd_suspend_one)):
        sp = sub.add_parser(name)
        sp.add_argument("--customer", type=int, required=True)
        sp.add_argument("--plan", default="TRIAL")
        sp.add_argument("--node", default="de1")
        sp.add_argument("--dry-run", action="store_true", default=True)
        sp.add_argument("--live", action="store_true")
        sp.add_argument("--confirm", action="store_true")
        sp.set_defaults(func=func)

    rp = sub.add_parser("reconcile-usage")
    rp.add_argument("--dry-run", action="store_true", default=True)
    rp.add_argument("--live", action="store_true")
    rp.add_argument("--confirm", action="store_true")
    rp.set_defaults(func=cmd_reconcile_usage)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

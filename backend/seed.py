"""Idempotent seed of the authoritative starting catalogue.

Seeds plans / regions / protocol profiles / entitlements / settings and the `de1` node
(status=test). Re-running is safe (INSERT OR IGNORE on unique keys). These are the
*starting* values only — all are admin-editable at runtime; nothing here is a code constant
that business logic depends on. Values are the authoritative catalogue (Plan_Rules / plan v1.9).

Note on units: `data_limit_gib` holds the plan's nominal cap number; conversion to Hiddify's
GB happens at the API boundary (see backend.units).
"""
from __future__ import annotations

import sqlite3

# (plan_code, name_en, data_limit_gib, duration_days, price_mmk, recommended_devices, is_trial, sort)
PLANS = [
    ("TRIAL",    "Trial",    10,   7,     0, 1, 1, 0),
    ("BASIC_1M", "Basic",    50,   30,  3000, 1, 0, 1),
    ("CORE_1M",  "Core",    100,   30,  5000, 2, 0, 2),
    ("PLUS_3M",  "Plus",    360,   90, 15000, 3, 0, 3),
    ("PRO_3M",   "Pro",     600,   90, 20000, 4, 0, 4),
    ("MAX_6M",   "Max",    1500,  180, 30000, 5, 0, 5),
]

# (region_code, display, status, is_default, is_premium_only, sort)
REGIONS = [
    ("de", "Germany",   "test",    1, 0, 0),
    ("us", "USA",       "planned", 0, 0, 1),
    ("sg", "Singapore", "planned", 0, 1, 2),  # SG = premium-only
]

# (profile_code, display_base, engine_protocol, is_fast_tier, sort)
PROFILES = [
    ("FAST1",  "Fast",   "hysteria2",     1, 0),
    ("FAST2",  "Fast",   "shadowsocks",   1, 1),
    ("SECURE", "Secure", "vless-reality", 0, 2),
]

# plan_code -> [region_code,...]
PLAN_REGIONS = {
    "TRIAL":    ["de"],
    "BASIC_1M": ["de"],
    "CORE_1M":  ["de", "us"],
    "PLUS_3M":  ["de", "us"],
    "PRO_3M":   ["de", "us", "sg"],   # SG premium-only → PRO/MAX
    "MAX_6M":   ["de", "us", "sg"],
}

# plan_code -> [profile_code,...]  (one fast tier = "Fast"; both = Fast1/Fast2)
PLAN_PROFILES = {
    "TRIAL":    ["FAST1", "SECURE"],
    "BASIC_1M": ["FAST1", "SECURE"],
    "CORE_1M":  ["FAST1", "SECURE"],
    "PLUS_3M":  ["FAST1", "FAST2", "SECURE"],
    "PRO_3M":   ["FAST1", "FAST2", "SECURE"],
    "MAX_6M":   ["FAST1", "FAST2", "SECURE"],
}

SETTINGS = [
    ("node_alert_warn_pct", "75", "WARN threshold (% of limit)"),
    ("node_alert_critical_pct", "90", "CRITICAL threshold (% of limit)"),
    ("referral_bonus_days_referrer", "0", "Referral reward (seed; tune later)"),
    ("referral_bonus_days_referee", "0", "Referral reward (seed; tune later)"),
    ("default_region_code", "de", "Default/entry region"),
]

# de1 node — status=test; secret API key by env handle only; provenance per ADR-002.
DE1_NODE = dict(
    node_code="de1", region_code="de",
    public_hostname="node-de.unseen.click", public_ip="5.249.160.59",
    status="test", is_master_colocated=0, api_secret_handle="NODE_DE1_API_KEY",
    est_vcpu=4, est_ram_mb=4096, est_disk_gb=25, est_bandwidth_gb=30000,
    det_os="Ubuntu 22.04.5 LTS", det_vcpu=4, det_ram_mb=1908, det_disk_gb=23,
    conf_bandwidth_gb=None, verification_status="detected",
    notes="Hiddify v12.3.3 installed (PASS w/ follow-ups). RAM balloon-dynamic "
          "(~1.8 idle/~3.8 load). Pre-live TODO: regenerate leaked default-user keys, "
          "open SS/UDP ports, lock 4GB RAM, disable SSH password login. NOT live.",
)


# (node_code, reason, sanitized detail) — Phase 7 data-driven live blockers.
NODE_LIVE_BLOCKERS = [
    ("de1", "leaked_key_rebuild_pending",
     "default-user/server keys exposed in earlier testing; rebuild node before live (no secrets here)"),
]


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def seed(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.executemany(
        "INSERT OR IGNORE INTO plans"
        "(plan_code,display_name_en,data_limit_gib,duration_days,price_mmk,"
        " recommended_device_count,is_trial,sort_order) VALUES (?,?,?,?,?,?,?,?)",
        PLANS,
    )
    cur.executemany(
        "INSERT OR IGNORE INTO proxy_regions"
        "(region_code,display_name,status,is_default,is_premium_only,sort_order)"
        " VALUES (?,?,?,?,?,?)",
        REGIONS,
    )
    cur.executemany(
        "INSERT OR IGNORE INTO protocol_profiles"
        "(profile_code,display_base,engine_protocol,is_fast_tier,sort_order)"
        " VALUES (?,?,?,?,?)",
        PROFILES,
    )
    for plan, regions in PLAN_REGIONS.items():
        cur.executemany(
            "INSERT OR IGNORE INTO plan_region_entitlements(plan_code,region_code) VALUES (?,?)",
            [(plan, r) for r in regions],
        )
    for plan, profs in PLAN_PROFILES.items():
        cur.executemany(
            "INSERT OR IGNORE INTO plan_protocol_entitlements(plan_code,profile_code) VALUES (?,?)",
            [(plan, p) for p in profs],
        )
    cur.executemany(
        "INSERT OR IGNORE INTO settings(key,value,description) VALUES (?,?,?)", SETTINGS
    )
    cols = ",".join(DE1_NODE.keys())
    qs = ",".join("?" for _ in DE1_NODE)
    cur.execute(
        f"INSERT OR IGNORE INTO proxy_nodes({cols}) VALUES ({qs})",
        tuple(DE1_NODE.values()),
    )
    # Phase 7: data-driven live blocker for de1 (leaked default-user/server keys → rebuild required
    # before live; docs/PHASE4_PRELIVE_DE1_TUNING.md). Admin-editable: delete the row once cleared.
    if _table_exists(conn, "node_live_blockers"):
        cur.executemany(
            "INSERT OR IGNORE INTO node_live_blockers(node_code,reason,detail) VALUES (?,?,?)",
            NODE_LIVE_BLOCKERS,
        )
    conn.commit()


def entitled_regions(conn: sqlite3.Connection, plan_code: str) -> list[str]:
    return [r[0] for r in conn.execute(
        "SELECT region_code FROM plan_region_entitlements WHERE plan_code=? ORDER BY region_code",
        (plan_code,)).fetchall()]


def entitled_profiles(conn: sqlite3.Connection, plan_code: str) -> list[str]:
    return [r[0] for r in conn.execute(
        "SELECT profile_code FROM plan_protocol_entitlements WHERE plan_code=? ORDER BY profile_code",
        (plan_code,)).fetchall()]

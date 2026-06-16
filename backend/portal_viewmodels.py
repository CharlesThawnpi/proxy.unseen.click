"""Sanitized viewmodels for the render-only customer portal foundation.

All functions return plain dictionaries/lists containing display-safe data. Templates still
HTML-escape every dynamic value, so DB-edited labels cannot become markup.
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from . import availability, delivery_payloads, entitlements, link_renderer

BRANDED_LINK_PLACEHOLDER = f"https://{link_renderer.BRANDED_HOST}{link_renderer.BRANDED_PATH}<opaque-token>"

_STATUS_LABELS = {
    "pending": ("စောင့်ဆိုင်းနေသည်", "warn"),
    "active": ("Active ဖြစ်သည်", "ok"),
    "expired": ("သက်တမ်းကုန်", "bad"),
    "suspended": ("ယာယီရပ်ဆိုင်း", "bad"),
    "dry_run_planned": ("Dry-run planned", "info"),
    "provision_failed": ("Provision failed", "bad"),
    "unprovisioned": ("မချိတ်ဆက်ရသေး", "neutral"),
    "provisioned": ("Provisioned", "ok"),
}

_REGION_STATUS = {
    "planned": ("Planned", "neutral"),
    "test": ("Test", "info"),
    "standby": ("Standby", "warn"),
    "live": ("Live", "ok"),
    "retired": ("Retired", "bad"),
}


def _badge(value: Optional[str]) -> dict:
    raw = str(value or "unknown")
    label, tone = _STATUS_LABELS.get(raw, (raw, "neutral"))
    return {"raw": raw, "label": label, "tone": tone}


def _region_status(value: Optional[str]) -> dict:
    raw = str(value or "planned")
    label, tone = _REGION_STATUS.get(raw, (raw, "neutral"))
    return {"raw": raw, "label": label, "tone": tone}


def _money_mmk(value: int) -> str:
    return f"{int(value):,} MMK"


def _region_rows(conn: sqlite3.Connection, codes: list[str]) -> dict[str, sqlite3.Row]:
    if not codes:
        return {}
    placeholders = ",".join("?" * len(codes))
    rows = conn.execute(
        f"SELECT * FROM proxy_regions WHERE region_code IN ({placeholders})", codes
    ).fetchall()
    return {r["region_code"]: r for r in rows}


def _availability_label(region: dict) -> dict:
    if region.get("available"):
        return {"label": "ရနိုင်သည်", "tone": "ok"}
    reasons = set(region.get("reasons") or [])
    if "node_status_test" in reasons:
        return {"label": "စမ်းသပ်နေဆဲ", "tone": "info"}
    if "node_status_planned" in reasons or "no_candidate_node" in reasons:
        return {"label": "မဖွင့်သေးပါ", "tone": "neutral"}
    if "node_down" in reasons:
        return {"label": "ယာယီမရနိုင်", "tone": "bad"}
    if "node_degraded" in reasons:
        return {"label": "အကန့်အသတ်ရှိ", "tone": "warn"}
    return {"label": "မရနိုင်ပါ", "tone": "warn"}


def _protocols_for_region(region: dict) -> list[dict]:
    out = []
    for proto in region.get("protocols") or []:
        out.append({
            "label": proto.get("label") or proto.get("profile_code"),
            "available": bool(proto.get("available")),
            "badge": {"label": "ရနိုင်", "tone": "ok"} if proto.get("available")
            else {"label": "Planned", "tone": "neutral"},
        })
    return out


def plans(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM plans WHERE is_public=1 AND is_enabled=1 ORDER BY sort_order, id"
    ).fetchall()
    out = []
    for row in rows:
        ent = entitlements.resolve(conn, row["plan_code"])
        av = availability.resolve(conn, row["plan_code"], mode=availability.MODE_DRY_RUN)
        region_by_code = _region_rows(conn, ent.regions)
        regions = []
        for code in ent.regions:
            rrow = region_by_code.get(code)
            region_av = av.regions.get(code, {"available": False, "reasons": []})
            premium = bool(rrow["is_premium_only"]) if rrow else False
            regions.append({
                "code": code.upper(),
                "name": rrow["display_name"] if rrow else code.upper(),
                "premium_only": premium,
                "status": _region_status(rrow["status"] if rrow else None),
                "availability": _availability_label(region_av),
                "protocols": _protocols_for_region(region_av),
            })
        protocols = [{"code": code, "label": ent.profile_labels.get(code, code)}
                     for code in ent.profiles]
        out.append({
            "plan_code": row["plan_code"],
            "name": row["display_name_my"] or row["display_name_en"],
            "name_en": row["display_name_en"],
            "data_limit": f"{int(row['data_limit_gib'])} GiB",
            "duration": f"{int(row['duration_days'])} days",
            "price": _money_mmk(row["price_mmk"]),
            "devices": str(row["recommended_device_count"] or "-"),
            "is_trial": bool(row["is_trial"]),
            "regions": regions,
            "protocols": protocols,
        })
    return out


def customer_dashboard(conn: sqlite3.Connection, customer_id: int) -> Optional[dict]:
    customer = conn.execute("SELECT * FROM customers WHERE id=? AND is_deleted=0", (customer_id,)).fetchone()
    if not customer:
        return None
    subs = conn.execute(
        "SELECT s.*, p.display_name_en FROM subscriptions s "
        "LEFT JOIN plans p ON p.plan_code=s.plan_code "
        "WHERE s.customer_id=? ORDER BY s.created_at DESC, s.id DESC",
        (customer_id,),
    ).fetchall()
    items = []
    for sub in subs:
        items.append(_subscription_summary(sub))
    active_count = sum(1 for sub in subs if sub["status"] == "active")
    return {
        "public_customer_code": customer["public_customer_code"] or "UP-PENDING",
        "preferred_language": customer["preferred_language"],
        "subscription_count": len(items),
        "active_count": active_count,
        "subscriptions": items,
    }


def _subscription_summary(sub: sqlite3.Row) -> dict:
    status = sub["provision_status"] if sub["provision_status"] in ("dry_run_planned", "provision_failed") else sub["status"]
    return {
        "id": int(sub["id"]),
        "customer_id": int(sub["customer_id"]),
        "code": f"SUB-{int(sub['id']):06d}",
        "plan_code": sub["plan_code"],
        "plan_name": sub["display_name_en"] or sub["plan_code"],
        "status": _badge(status),
        "life_status": _badge(sub["status"]),
        "provision_status": _badge(sub["provision_status"]),
        "data_limit": f"{int(sub['snap_data_limit_gib'])} GiB",
        "duration": f"{int(sub['snap_duration_days'])} days",
        "price": _money_mmk(sub["snap_price_mmk"]),
        "start_date": sub["start_date"] or "မစရသေးပါ",
        "expiry_date": sub["expiry_date"] or "မသတ်မှတ်ရသေးပါ",
    }


def subscription_detail(conn: sqlite3.Connection, subscription_id: int) -> Optional[dict]:
    sub = conn.execute(
        "SELECT s.*, p.display_name_en, c.public_customer_code FROM subscriptions s "
        "JOIN customers c ON c.id=s.customer_id "
        "LEFT JOIN plans p ON p.plan_code=s.plan_code "
        "WHERE s.id=? AND c.is_deleted=0",
        (subscription_id,),
    ).fetchone()
    if not sub:
        return None
    summary = _subscription_summary(sub)
    av = availability.resolve(conn, sub["plan_code"], mode=availability.MODE_DRY_RUN)
    region_by_code = _region_rows(conn, av.entitled_regions)
    regions = []
    for code in av.entitled_regions:
        rrow = region_by_code.get(code)
        region_av = av.regions.get(code, {"available": False, "reasons": []})
        regions.append({
            "code": code.upper(),
            "name": rrow["display_name"] if rrow else code.upper(),
            "availability": _availability_label(region_av),
            "protocols": _protocols_for_region(region_av),
        })
    delivery = delivery_status(conn, int(sub["id"]))
    return {
        **summary,
        "public_customer_code": sub["public_customer_code"] or "UP-PENDING",
        "regions": regions,
        "delivery": delivery,
    }


def delivery_status(conn: sqlite3.Connection, subscription_id: int) -> dict:
    row = conn.execute(
        "SELECT * FROM subscription_deliveries WHERE subscription_id=? ORDER BY created_at DESC, id DESC LIMIT 1",
        (subscription_id,),
    ).fetchone()
    if row:
        deep = bool(row["deep_link_available"])
        copy = bool(row["copy_link_available"])
        qr = bool(row["qr_available"])
        primary = row["primary_mode"]
        status = row["status"]
    else:
        deep = False
        copy = False
        qr = False
        primary = delivery_payloads.MODE_COPY_LINK
        status = "planned"
    return {
        "placeholder": BRANDED_LINK_PLACEHOLDER,
        "primary_mode": primary,
        "status": _badge(status),
        "modes": [
            {"label": "Deep-link", "badge": {"label": "Available", "tone": "ok"} if deep else {"label": "Planned", "tone": "neutral"}},
            {"label": "Copy-link", "badge": {"label": "Available", "tone": "ok"} if copy else {"label": "Planned", "tone": "neutral"}},
            {"label": "QR", "badge": {"label": "Available", "tone": "ok"} if qr else {"label": "Planned", "tone": "neutral"}},
        ],
    }


def first_customer_id(conn: sqlite3.Connection) -> Optional[int]:
    row = conn.execute("SELECT id FROM customers WHERE is_deleted=0 ORDER BY id LIMIT 1").fetchone()
    return int(row[0]) if row else None


def sample_data(conn: sqlite3.Connection) -> dict:
    """Create deterministic dry-run sample data in a temp DB only.

    This uses the same account/subscription tables as the product, but stores no private profile
    data and no delivery token. Callers choose the temp DB path.
    """
    from . import account_service

    cid = account_service.resolve_customer(conn, "web", "portal-sample")
    existing = conn.execute("SELECT id FROM subscriptions WHERE customer_id=? ORDER BY id LIMIT 1", (cid,)).fetchone()
    if existing:
        return {"customer_id": cid, "subscription_id": int(existing[0])}
    cur = conn.execute(
        "INSERT INTO subscriptions(customer_id, plan_code, snap_data_limit_gib, snap_duration_days, "
        "snap_price_mmk, status, provision_status, start_date, expiry_date) "
        "VALUES (?,?,?,?,?, 'pending', 'dry_run_planned', '2026-06-16 00:00:00', '2026-09-14 00:00:00')",
        (cid, "PRO_3M", 600, 90, 20000),
    )
    sid = int(cur.lastrowid)
    conn.commit()
    return {"customer_id": cid, "subscription_id": sid}


def add_preview_degraded_state(conn: sqlite3.Connection) -> None:
    """Add safe degraded/unavailable sample rows for local preview HTML.

    These rows are temp-DB-only synthetic state. No node is contacted and no real operational
    hostname, IP, token, or customer data is introduced.
    """
    conn.execute(
        "INSERT OR IGNORE INTO proxy_nodes(node_code, region_code, status) VALUES ('us-preview', 'us', 'live')"
    )
    conn.execute(
        "INSERT OR IGNORE INTO proxy_nodes(node_code, region_code, status) VALUES ('sg-preview', 'sg', 'live')"
    )
    conn.execute(
        "INSERT INTO node_alerts(node_code, level, metric) VALUES ('us-preview', 'WARN', 'preview_health')"
    )
    conn.execute(
        "INSERT INTO node_alerts(node_code, level, metric) VALUES ('sg-preview', 'DOWN', 'preview_health')"
    )
    conn.commit()

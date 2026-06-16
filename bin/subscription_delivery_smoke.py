#!/usr/bin/env python3
"""Subscription delivery smoke (TEMP DB; MOCKED Hiddify output; NO network, NO send, NO raw links).

Builds a synthetic customer + subscription + access profile on a temp DB, feeds a MOCKED Hiddify
subscription output, prepares a dry-run delivery (safe refs only), and prints a sanitized summary.
Asserts the DB row stores no raw link and that the raw branded token is not persisted.

  python3 bin/subscription_delivery_smoke.py --db /tmp/deliv_smoke.sqlite3
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import (  # noqa: E402
    access_profile_service, account_service, db as dbmod, link_renderer, migrate,
    notification_service as notif, seed, subscription_delivery,
)

# A MOCK of what de1 *would* return — kept in memory only, never committed as a real link.
_MOCK_OUTPUT = {
    "all_configs": [
        {"protocol": "hysteria2", "name": "FAST1"},
        {"protocol": "shadowsocks", "name": "FAST2"},
        {"protocol": "vless-reality", "name": "Secure"},
    ],
    "deep_link": "hiddify://import/EXAMPLE-PLACEHOLDER",   # mock; not a real link
    "subscription_url": "https://example.invalid/s/EXAMPLE-PLACEHOLDER",
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Subscription delivery smoke (temp DB, mocked output).")
    ap.add_argument("--db", default="/tmp/unseenproxy_deliv_smoke.sqlite3")
    args = ap.parse_args(argv)

    migrate.migrate_path(args.db)
    conn = dbmod.connect(args.db)
    seed.seed(conn)

    cid = account_service.resolve_customer(conn, "telegram", "800100")
    cur = conn.execute(
        "INSERT INTO subscriptions(customer_id, plan_code, snap_data_limit_gib, snap_duration_days, "
        "snap_price_mmk, status, provision_status) VALUES (?,?,?,?,?, 'pending', 'dry_run_planned')",
        (cid, "PRO_3M", 600, 90, 20000))
    sid = int(cur.lastrowid)
    conn.commit()
    ap_res = access_profile_service.create_or_reuse(conn, cid)

    # The raw opaque token lives ONLY here in memory; only its hash is persisted.
    raw_token = "EXAMPLE-OPAQUE-TOKEN-not-real"
    res = subscription_delivery.prepare_delivery(
        conn, customer_id=cid, subscription_id=sid, access_profile_id=ap_res.access_profile_id,
        mocked_hiddify_output=_MOCK_OUTPUT, raw_branded_token=raw_token, channel="telegram")

    row = conn.execute("SELECT * FROM subscription_deliveries WHERE id=?", (res.delivery_id,)).fetchone()
    print(json.dumps({
        "delivery_id": res.delivery_id,
        "notification_id": res.notification_id,
        "primary_mode": res.payload.primary_mode,
        "deep_link_available": res.payload.deep_link_available,
        "copy_link_available": res.payload.copy_link_available,
        "qr_available": res.payload.qr_available,
        "branded_token_sha256_len": len(row["branded_token_sha256"] or ""),
        "queue_counts": notif.queue_counts(conn),
        "preview": subscription_delivery.render_preview(res.payload),
    }, ensure_ascii=False, indent=2))

    # Safety asserts: no raw link/token persisted; branded link only derivable in memory + redacted.
    stored = " ".join(str(v) for v in dict(row).values())
    assert "hiddify://" not in stored and "://" not in stored.replace("status", ""), "raw link in DB row!"
    assert raw_token not in stored, "raw token persisted!"
    assert link_renderer.redact_link(subscription_delivery.build_branded_link_in_memory(raw_token)) \
        == "branded:sub.unseen.click/s/<redacted>"
    print("SMOKE_OK: refs-only persisted; raw token/link not stored; no network/send.")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

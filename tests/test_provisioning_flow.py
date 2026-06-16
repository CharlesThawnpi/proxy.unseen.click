import os
import tempfile
import unittest

from _helper import fresh_db
from backend import (
    account_service, compensation, config, idempotency,
    payment_approval_service as appr, provisioning_service as prov,
)

NOW = "2026-06-16 00:00:00"


def _order(conn, plan_code="PRO_3M", platform_id="buyer-1"):
    cid = account_service.resolve_customer(conn, "telegram", platform_id)
    price = conn.execute("SELECT price_mmk FROM plans WHERE plan_code=?", (plan_code,)).fetchone()[0]
    cur = conn.execute(
        "INSERT INTO payment_orders(customer_id, plan_code, amount_mmk, status) VALUES (?,?,?, 'pending')",
        (cid, plan_code, int(price)))
    conn.commit()
    return cid, int(cur.lastrowid)


class TestApproval(unittest.TestCase):
    def setUp(self):
        self.conn = fresh_db(os.path.join(tempfile.mkdtemp(), "t.sqlite3"))

    def tearDown(self):
        self.conn.close()

    def test_approval_creates_exactly_one_subscription(self):
        _, oid = _order(self.conn, "BASIC_1M")
        r = appr.approve_order_dry_run(self.conn, oid, now=NOW)
        self.assertFalse(r.duplicate)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM subscriptions").fetchone()[0], 1)
        # order transitioned to approved with a timestamp
        row = self.conn.execute("SELECT status, approved_at FROM payment_orders WHERE id=?", (oid,)).fetchone()
        self.assertEqual(row["status"], "approved")
        self.assertIsNotNone(row["approved_at"])

    def test_duplicate_approval_replays_same_result(self):
        _, oid = _order(self.conn, "BASIC_1M")
        r1 = appr.approve_order_dry_run(self.conn, oid, now=NOW)
        r2 = appr.approve_order_dry_run(self.conn, oid, now=NOW)
        self.assertTrue(r2.duplicate)
        self.assertEqual(r1.subscription_id, r2.subscription_id)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM subscriptions").fetchone()[0], 1)

    def test_plan_snapshots_copied(self):
        _, oid = _order(self.conn, "PRO_3M")
        r = appr.approve_order_dry_run(self.conn, oid, now=NOW)
        sub = self.conn.execute("SELECT * FROM subscriptions WHERE id=?", (r.subscription_id,)).fetchone()
        plan = self.conn.execute("SELECT * FROM plans WHERE plan_code='PRO_3M'").fetchone()
        self.assertEqual(sub["snap_data_limit_gib"], plan["data_limit_gib"])
        self.assertEqual(sub["snap_duration_days"], plan["duration_days"])
        self.assertEqual(sub["snap_price_mmk"], plan["price_mmk"])
        # deterministic dates: expiry = start + duration_days
        self.assertEqual(sub["start_date"], NOW)
        exp = self.conn.execute("SELECT datetime(?, ?)", (NOW, f"+{plan['duration_days']} days")).fetchone()[0]
        self.assertEqual(sub["expiry_date"], exp)

    def test_snapshot_immune_to_later_catalogue_change(self):
        _, oid = _order(self.conn, "PRO_3M")
        r = appr.approve_order_dry_run(self.conn, oid, now=NOW)
        before = self.conn.execute("SELECT snap_price_mmk FROM subscriptions WHERE id=?",
                                   (r.subscription_id,)).fetchone()[0]
        # admin later changes the plan price/quota
        self.conn.execute("UPDATE plans SET price_mmk=999999, data_limit_gib=99999 WHERE plan_code='PRO_3M'")
        self.conn.commit()
        after = self.conn.execute("SELECT snap_price_mmk, snap_data_limit_gib FROM subscriptions WHERE id=?",
                                  (r.subscription_id,)).fetchone()
        self.assertEqual(after["snap_price_mmk"], before)        # unchanged snapshot
        self.assertNotEqual(after["snap_data_limit_gib"], 99999)

    def test_access_profile_no_raw_token(self):
        _, oid = _order(self.conn, "BASIC_1M")
        r = appr.approve_order_dry_run(self.conn, oid, now=NOW)
        ap = self.conn.execute("SELECT token_sha256, hiddify_uuid FROM access_profiles WHERE id=?",
                               (r.access_profile_id,)).fetchone()
        self.assertEqual(len(ap["token_sha256"]), 64)            # a hash, not a raw token
        self.assertIsNone(ap["hiddify_uuid"])                    # no UUID in dry-run
        # exactly one access profile, reused on duplicate approval
        appr.approve_order_dry_run(self.conn, oid, now=NOW)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM access_profiles").fetchone()[0], 1)


class TestProvisioningFlow(unittest.TestCase):
    def setUp(self):
        self.conn = fresh_db(os.path.join(tempfile.mkdtemp(), "t.sqlite3"))

    def tearDown(self):
        self.conn.close()
        os.environ.pop(config.LIVE_ENV_LATCH, None)

    def test_flow_exactly_once(self):
        _, oid = _order(self.conn, "PRO_3M")
        prov.dry_run_provision_flow(self.conn, oid, node_code="de1", now=NOW)
        prov.dry_run_provision_flow(self.conn, oid, node_code="de1", now=NOW)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM subscriptions").fetchone()[0], 1)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM outbound_messages").fetchone()[0], 1)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM provisioning_attempts").fetchone()[0], 1)

    def test_provision_status_and_delivery_payload_ref(self):
        _, oid = _order(self.conn, "BASIC_1M")
        res = prov.dry_run_provision_flow(self.conn, oid, node_code="de1", now=NOW)
        sub = self.conn.execute("SELECT provision_status FROM subscriptions WHERE id=?",
                                (res.subscription_id,)).fetchone()
        self.assertEqual(sub["provision_status"], "dry_run_planned")
        msg = self.conn.execute("SELECT channel, purpose, status, payload_ref FROM outbound_messages "
                                "WHERE id=?", (res.provision.notification_id,)).fetchone()
        self.assertEqual(msg["status"], "queued")
        self.assertEqual(msg["payload_ref"], f"delivery:sub:{res.subscription_id}")
        # payload_ref is a reference, not a link/body
        for needle in ("http", "://", "vless", "ss:", "hy2"):
            self.assertNotIn(needle, msg["payload_ref"])

    def test_live_refused_even_with_env_and_flags(self):
        _, oid = _order(self.conn, "PRO_3M")
        appr.approve_order_dry_run(self.conn, oid, now=NOW)
        sid = self.conn.execute("SELECT id FROM subscriptions WHERE id=1").fetchone()[0]
        os.environ[config.LIVE_ENV_LATCH] = "1"      # env latch ON
        r = prov.plan_and_dry_run_provision(self.conn, sid, node_code="de1", live=True, confirm=True)
        self.assertTrue(r.live_refused)
        self.assertIn("phase4c_live_disabled", r.live_blockers)
        self.assertIn("leaked_key_rebuild_pending", r.live_blockers)
        # no Hiddify user row could exist (we have no such table) and provision stays dry-run
        self.assertEqual(r.provision_status, "dry_run_planned")

    def test_de1_test_status_blocks_live(self):
        _, oid = _order(self.conn, "TRIAL")
        res = prov.dry_run_provision_flow(self.conn, oid, node_code="de1", now=NOW)
        self.assertIn("node_not_live:test", res.provision.live_blockers)

    def test_idempotency_keys_recorded(self):
        _, oid = _order(self.conn, "BASIC_1M")
        res = prov.dry_run_provision_flow(self.conn, oid, node_code="de1", now=NOW)
        self.assertEqual(idempotency.status_of(self.conn, "payment_approval", f"order:{oid}"), "completed")
        self.assertEqual(idempotency.status_of(self.conn, "provision_subscription",
                                               f"sub:{res.subscription_id}"), "completed")

    def test_flow_makes_no_network_call(self):
        # Patch urllib so ANY real HTTP attempt during the flow would raise — proving the
        # dry-run path never touches the network (Hiddify client used only for path builders).
        import urllib.request
        _, oid = _order(self.conn, "PRO_3M")
        orig = urllib.request.urlopen
        urllib.request.urlopen = lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("network call attempted in dry-run!"))
        try:
            res = prov.dry_run_provision_flow(self.conn, oid, node_code="de1", now=NOW)
            self.assertEqual(res.provision.provision_status, "dry_run_planned")
        finally:
            urllib.request.urlopen = orig

    def test_audit_rows_sanitized(self):
        _, oid = _order(self.conn, "PRO_3M")
        res = prov.dry_run_provision_flow(self.conn, oid, node_code="de1", now=NOW)
        actions = {r[0] for r in self.conn.execute("SELECT action FROM audit_logs").fetchall()}
        for a in ("payment_approval_dry_run", "subscription_plan_created",
                  "provisioning_dry_run_planned", "notification_queued"):
            self.assertIn(a, actions)
        blob = " ".join(r[0] for r in self.conn.execute("SELECT detail FROM audit_logs").fetchall())
        for needle in ("Hiddify-API-Key", "vless://", "ss://", "hy2://", "BEGIN", "uuid="):
            self.assertNotIn(needle, blob)


class TestCompensation(unittest.TestCase):
    def setUp(self):
        self.conn = fresh_db(os.path.join(tempfile.mkdtemp(), "t.sqlite3"))

    def tearDown(self):
        self.conn.close()

    def test_provision_failed_keeps_rows_forward_only(self):
        _, oid = _order(self.conn, "BASIC_1M")
        r = appr.approve_order_dry_run(self.conn, oid, now=NOW)
        compensation.mark_provision_failed(self.conn, r.subscription_id, "de1", "simulated_failure")
        sub = self.conn.execute("SELECT provision_status FROM subscriptions WHERE id=?",
                                (r.subscription_id,)).fetchone()
        self.assertEqual(sub["provision_status"], "provision_failed")
        # subscription + order rows are KEPT (no destructive rollback)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM subscriptions").fetchone()[0], 1)
        self.assertEqual(self.conn.execute("SELECT status FROM payment_orders WHERE id=?", (oid,)).fetchone()[0],
                         "approved")
        att = self.conn.execute("SELECT outcome FROM provisioning_attempts WHERE subscription_id=?",
                                (r.subscription_id,)).fetchone()
        self.assertEqual(att["outcome"], "failed")

    def test_delivery_retry_flag_keeps_subscription(self):
        _, oid = _order(self.conn, "BASIC_1M")
        r = appr.approve_order_dry_run(self.conn, oid, now=NOW)
        compensation.flag_delivery_retry(self.conn, r.subscription_id, "enqueue_error")
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM subscriptions").fetchone()[0], 1)
        actions = {r[0] for r in self.conn.execute("SELECT action FROM audit_logs").fetchall()}
        self.assertIn("delivery_enqueue_failed_retry_flagged", actions)


if __name__ == "__main__":
    unittest.main()

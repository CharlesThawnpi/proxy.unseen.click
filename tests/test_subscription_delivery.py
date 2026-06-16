import os
import tempfile
import unittest

from _helper import fresh_db
from backend import (
    access_profile_service, account_service, delivery_payloads, hiddify_subscription_output as hout,
    link_renderer, notification_service as notif, qr_renderer, subscription_delivery,
)

# In-memory MOCK of de1 output (never a real link; placeholders only).
MOCK_OUTPUT = {
    "all_configs": [
        {"protocol": "hysteria2", "name": "FAST1"},
        {"protocol": "shadowsocks", "name": "FAST2"},
        {"protocol": "vless-reality", "name": "Secure"},
    ],
    "deep_link": "hiddify://import/EXAMPLE",
    "subscription_url": "https://example.invalid/s/EXAMPLE",
}
RAW_TOKEN = "EXAMPLE-OPAQUE-TOKEN-not-real"


def _seed_customer_sub(conn, tg_id="800100"):
    cid = account_service.resolve_customer(conn, "telegram", tg_id)
    cur = conn.execute(
        "INSERT INTO subscriptions(customer_id, plan_code, snap_data_limit_gib, snap_duration_days, "
        "snap_price_mmk, status, provision_status) VALUES (?,?,?,?,?, 'pending', 'dry_run_planned')",
        (cid, "PRO_3M", 600, 90, 20000))
    sid = int(cur.lastrowid)
    conn.commit()
    ap = access_profile_service.create_or_reuse(conn, cid)
    return cid, sid, ap.access_profile_id


class TestLinkRenderer(unittest.TestCase):
    def test_branded_shape_and_token_handle(self):
        link = link_renderer.branded_link(RAW_TOKEN)
        self.assertTrue(link.startswith("https://sub.unseen.click/s/"))
        self.assertTrue(link_renderer.is_branded_link(link))
        h = link_renderer.branded_token_handle(RAW_TOKEN)
        self.assertEqual(len(h), 64)            # sha256 hex
        self.assertNotIn(RAW_TOKEN, h)          # raw token not recoverable from the handle

    def test_redaction(self):
        self.assertEqual(link_renderer.redact_link(link_renderer.branded_link(RAW_TOKEN)),
                         "branded:sub.unseen.click/s/<redacted>")
        self.assertEqual(link_renderer.redact_link("hiddify://import/x"), "raw:hiddify:<redacted>")
        self.assertEqual(link_renderer.redact_link("vless://payload"), "raw:vless:<redacted>")
        self.assertEqual(link_renderer.redact_link(None), "link:<absent>")

    def test_raw_proxy_link_detection(self):
        for raw in ("hiddify://import/x", "vless://abc", "ss://abc", "hy2://abc",
                    "https://host/api/v2/admin/x", "https://host/all-configs/?uuid=x"):
            self.assertTrue(link_renderer.looks_like_raw_proxy_link(raw), raw)
        self.assertFalse(link_renderer.looks_like_raw_proxy_link("https://sub.unseen.click/s/tok"))


class TestHiddifyOutputNormalize(unittest.TestCase):
    def test_normalize_to_sanitized_summary(self):
        s = hout.normalize(MOCK_OUTPUT)
        self.assertEqual(s.profiles_count, 3)
        self.assertEqual(set(s.protocols), {"hysteria2", "shadowsocks", "vless-reality"})
        self.assertTrue(s.has_deep_link)
        self.assertTrue(s.has_subscription_url)
        # summary carries NO raw link/uuid/payload
        blob = str(s.as_dict())
        for needle in ("hiddify://", "vless://", "ss://", "://example", "EXAMPLE"):
            self.assertNotIn(needle, blob)

    def test_normalize_handles_bad_input(self):
        self.assertEqual(hout.normalize(None).profiles_count, 0)
        self.assertEqual(hout.normalize({}).profiles_count, 0)


class TestQrHonest(unittest.TestCase):
    def test_qr_is_planned_not_generated(self):
        plan = qr_renderer.qr_plan()
        self.assertFalse(plan.available)
        self.assertEqual(plan.status, "planned")
        self.assertFalse(qr_renderer.QR_IMPLEMENTED)


class TestDeliveryPayload(unittest.TestCase):
    def test_mode_priority(self):
        self.assertEqual(delivery_payloads.DeliveryPayload.choose_primary_mode(True, True, False),
                         delivery_payloads.MODE_DEEP_LINK)
        self.assertEqual(delivery_payloads.DeliveryPayload.choose_primary_mode(False, True, False),
                         delivery_payloads.MODE_COPY_LINK)
        self.assertEqual(delivery_payloads.DeliveryPayload.choose_primary_mode(False, False, True),
                         delivery_payloads.MODE_QR)
        # safe default = copy_link (branded copy always derivable)
        self.assertEqual(delivery_payloads.DeliveryPayload.choose_primary_mode(False, False, False),
                         delivery_payloads.MODE_COPY_LINK)


class TestPrepareDelivery(unittest.TestCase):
    def setUp(self):
        self.conn = fresh_db(os.path.join(tempfile.mkdtemp(), "t.sqlite3"))
        self.cid, self.sid, self.apid = _seed_customer_sub(self.conn)

    def tearDown(self):
        self.conn.close()

    def _prepare(self):
        return subscription_delivery.prepare_delivery(
            self.conn, customer_id=self.cid, subscription_id=self.sid,
            access_profile_id=self.apid, mocked_hiddify_output=MOCK_OUTPUT,
            raw_branded_token=RAW_TOKEN, channel="telegram")

    def test_payload_refs_only_and_deep_link_priority(self):
        res = self._prepare()
        p = res.payload
        self.assertEqual(p.customer_id, self.cid)
        self.assertEqual(p.subscription_id, self.sid)
        self.assertEqual(p.access_profile_id, self.apid)
        self.assertTrue(p.deep_link_available)
        self.assertTrue(p.copy_link_available)
        self.assertFalse(p.qr_available)
        self.assertEqual(p.primary_mode, delivery_payloads.MODE_DEEP_LINK)
        self.assertEqual(p.template_key, f"delivery:sub:{self.sid}")

    def test_branded_token_stored_as_hash_not_raw(self):
        res = self._prepare()
        row = self.conn.execute("SELECT * FROM subscription_deliveries WHERE id=?",
                                (res.delivery_id,)).fetchone()
        self.assertEqual(row["branded_token_sha256"], link_renderer.branded_token_handle(RAW_TOKEN))
        self.assertEqual(len(row["branded_token_sha256"]), 64)
        # full row contains no raw token and no raw link
        blob = " ".join(str(v) for v in dict(row).values())
        self.assertNotIn(RAW_TOKEN, blob)
        for needle in ("hiddify://", "vless://", "ss://", "hy2://", "/api/v2/", "all-configs"):
            self.assertNotIn(needle, blob)

    def test_notification_enqueued_payload_ref_only(self):
        res = self._prepare()
        row = notif.get_message(self.conn, res.notification_id)
        self.assertEqual(row["status"], "queued")
        self.assertEqual(row["payload_ref"], f"delivery:sub:{self.sid}")
        for needle in ("http", "://", "vless", "ss:", "hy2", "hiddify"):
            self.assertNotIn(needle, str(row["payload_ref"]))

    def test_preview_has_no_raw_link(self):
        res = self._prepare()
        preview = subscription_delivery.render_preview(res.payload)
        for needle in ("http", "://", "vless", "ss:", "hy2", "hiddify", RAW_TOKEN):
            self.assertNotIn(needle, preview)

    def test_audit_sanitized_no_secrets(self):
        self._prepare()
        blob = " ".join(r[0] for r in self.conn.execute("SELECT detail FROM audit_logs").fetchall())
        for needle in ("hiddify://", "vless://", "ss://", "hy2://", RAW_TOKEN, "/api/v2/", "all-configs"):
            self.assertNotIn(needle, blob)
        actions = {r[0] for r in self.conn.execute("SELECT action FROM audit_logs").fetchall()}
        self.assertIn("delivery_prepared", actions)
        self.assertIn("delivery_queued", actions)

    def test_refuses_to_persist_raw_link_as_template(self):
        # If a caller somehow passes a raw link where a template key belongs, persistence refuses.
        with self.assertRaises(subscription_delivery.RawLinkPersistenceError):
            subscription_delivery._guard_no_raw_link("hiddify://import/x")

    def test_no_db_column_for_raw_link(self):
        cols = {r[1] for r in self.conn.execute("PRAGMA table_info(subscription_deliveries)")}
        # there is deliberately no column that could hold a raw link/url/qr payload
        for forbidden in ("subscription_url", "raw_link", "deep_link", "qr_payload", "url", "link"):
            self.assertNotIn(forbidden, cols)


class TestNoNetwork(unittest.TestCase):
    def test_prepare_makes_no_network_call(self):
        import urllib.request
        conn = fresh_db(os.path.join(tempfile.mkdtemp(), "t.sqlite3"))
        cid, sid, apid = _seed_customer_sub(conn, tg_id="800200")
        orig = urllib.request.urlopen
        urllib.request.urlopen = lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("network call attempted during delivery prepare!"))
        try:
            subscription_delivery.prepare_delivery(
                conn, customer_id=cid, subscription_id=sid, access_profile_id=apid,
                mocked_hiddify_output=MOCK_OUTPUT, raw_branded_token=RAW_TOKEN)
        finally:
            urllib.request.urlopen = orig
        conn.close()


if __name__ == "__main__":
    unittest.main()

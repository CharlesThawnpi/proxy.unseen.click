import os
import re
import socket
import subprocess
import tempfile
import unittest
from pathlib import Path

from _helper import fresh_db
from backend import account_service, portal_app, portal_static, portal_viewmodels

REPO_ROOT = Path(__file__).resolve().parent.parent


FORBIDDEN_PAGE_NEEDLES = (
    "5.249.160.59",
    "node-de.unseen.click",
    "Hiddify-API-Key",
    "/api/v2/",
    "vless://",
    "ss://",
    "hy2://",
    "hiddify://",
    "EXAMPLE-OPAQUE-TOKEN",
)


def _sample(conn):
    return portal_viewmodels.sample_data(conn)


class TestPortalRendering(unittest.TestCase):
    def setUp(self):
        self.conn = fresh_db(os.path.join(tempfile.mkdtemp(), "portal.sqlite3"))
        self.sample = _sample(self.conn)

    def tearDown(self):
        self.conn.close()

    def render(self, path):
        return portal_app.render(self.conn, path, customer_id=self.sample["customer_id"])

    def assertSafe(self, html):
        for needle in FORBIDDEN_PAGE_NEEDLES:
            self.assertNotIn(needle, html)
        self.assertIsNone(re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", html, re.I))

    def test_landing_home_renders(self):
        res = self.render("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("UNSEEN PROXY", res.body)
        self.assertIn("Customer Portal", res.body)
        self.assertIn("Plan, subscription status", res.body)
        self.assertSafe(res.body)

    def test_plans_render_from_db_and_escape(self):
        self.conn.execute(
            "UPDATE plans SET display_name_en=? WHERE plan_code='BASIC_1M'",
            ("Basic <script>alert(1)</script>",),
        )
        self.conn.commit()
        res = self.render("/plans")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Basic &lt;script&gt;alert(1)&lt;/script&gt;", res.body)
        self.assertNotIn("Basic <script>", res.body)
        self.assertIn("PRO_3M", res.body)
        self.assertSafe(res.body)

    def test_sg_only_for_pro_max(self):
        plans = portal_viewmodels.plans(self.conn)
        by_code = {p["plan_code"]: p for p in plans}
        for plan in ("TRIAL", "BASIC_1M", "CORE_1M", "PLUS_3M"):
            self.assertNotIn("SG", {r["code"] for r in by_code[plan]["regions"]})
        for plan in ("PRO_3M", "MAX_6M"):
            self.assertIn("SG", {r["code"] for r in by_code[plan]["regions"]})

    def test_fast_display_rule(self):
        plans = portal_viewmodels.plans(self.conn)
        by_code = {p["plan_code"]: p for p in plans}
        basic_protocols = {p["label"] for p in by_code["BASIC_1M"]["protocols"]}
        plus_protocols = {p["label"] for p in by_code["PLUS_3M"]["protocols"]}
        self.assertIn("Fast", basic_protocols)
        self.assertNotIn("Fast1", basic_protocols)
        self.assertIn("Fast1", plus_protocols)
        self.assertIn("Fast2", plus_protocols)

    def test_dashboard_uses_public_customer_code_not_platform_id(self):
        res = self.render("/customer/status")
        code = account_service.public_code(self.conn, self.sample["customer_id"])
        self.assertIn(code, res.body)
        self.assertNotIn("portal-sample", res.body)
        self.assertNotIn("platform_user_id", res.body)
        self.assertSafe(res.body)

    def test_subscription_status_snapshot_and_safe_statuses(self):
        res = self.render(f"/subscriptions/{self.sample['subscription_id']}")
        self.assertEqual(res.status_code, 200)
        self.assertIn("600 GiB", res.body)
        self.assertIn("90 days", res.body)
        self.assertIn("20,000 MMK", res.body)
        self.assertIn("Dry-run planned", res.body)
        self.assertIn("Provision", res.body)
        self.assertIn("Subscription quick status", res.body)
        self.assertSafe(res.body)

    def test_key_status_badges_render(self):
        cases = [
            ("pending", "unprovisioned", "စောင့်ဆိုင်းနေသည်"),
            ("active", "provisioned", "Active ဖြစ်သည်"),
            ("expired", "unprovisioned", "သက်တမ်းကုန်"),
            ("suspended", "unprovisioned", "ယာယီရပ်ဆိုင်း"),
            ("active", "provision_failed", "Provision failed"),
            ("pending", "dry_run_planned", "Dry-run planned"),
        ]
        for life, provision, expected in cases:
            with self.subTest(life=life, provision=provision):
                self.conn.execute(
                    "UPDATE subscriptions SET status=?, provision_status=? WHERE id=?",
                    (life, provision, self.sample["subscription_id"]),
                )
                self.conn.commit()
                res = self.render(f"/subscriptions/{self.sample['subscription_id']}")
                self.assertIn(expected, res.body)
                self.assertSafe(res.body)

    def test_branded_link_placeholder_without_raw_token(self):
        res = self.render(f"/subscriptions/{self.sample['subscription_id']}")
        self.assertIn("https://sub.unseen.click/s/&lt;opaque-token&gt;", res.body)
        self.assertNotIn("example-opaque-token", res.body)
        branded = self.render("/s/<opaque-token>")
        self.assertEqual(branded.status_code, 200)
        self.assertIn("/s/&lt;opaque-token&gt;", branded.body)
        self.assertSafe(branded.body)

    def test_availability_messages_are_sanitized(self):
        res = self.render(f"/subscriptions/{self.sample['subscription_id']}")
        self.assertIn("Availability", res.body)
        self.assertIn("SG", res.body)
        self.assertIn("Node hostname/IP မပြပါ", res.body)
        self.assertSafe(res.body)

    def test_degraded_and_unavailable_pages_render_safely(self):
        degraded = self.render("/degraded")
        unavailable = self.render("/unavailable")
        self.assertEqual(degraded.status_code, 200)
        self.assertEqual(unavailable.status_code, 503)
        self.assertIn("အကန့်အသတ်ရှိ", degraded.body)
        self.assertIn("ယာယီမရနိုင်", unavailable.body)
        self.assertSafe(degraded.body)
        self.assertSafe(unavailable.body)

    def test_html_escaping_for_dynamic_subscription_status(self):
        self.conn.execute(
            "UPDATE subscriptions SET status=?, provision_status=? WHERE id=?",
            ("active<script>", "provision_failed<script>", self.sample["subscription_id"]),
        )
        self.conn.commit()
        res = self.render(f"/subscriptions/{self.sample['subscription_id']}")
        self.assertIn("provision_failed&lt;script&gt;", res.body)
        self.assertNotIn("provision_failed<script>", res.body)

    def test_css_is_compact_responsive_and_local(self):
        css = portal_static.PORTAL_CSS
        self.assertIn("@media (min-width: 760px)", css)
        self.assertIn("@media (max-width: 720px)", css)
        self.assertIn("@media (max-width: 480px)", css)
        self.assertIn(".grid.three", css)
        self.assertIn("overflow-x: hidden", css)
        self.assertIn('content: attr(data-label)', css)
        self.assertNotIn("@import", css)
        self.assertNotIn("url(", css)
        page = self.render("/plans").body
        for needle in ("cdn.", "fonts.googleapis", "<script", "<img", "http://", "https://fonts"):
            self.assertNotIn(needle, page)

    def test_no_network_or_server_started(self):
        original_socket = socket.socket

        def fail_socket(*args, **kwargs):
            raise AssertionError("socket/server attempted during portal render")

        socket.socket = fail_socket
        try:
            res = self.render("/plans")
        finally:
            socket.socket = original_socket
        self.assertEqual(res.status_code, 200)


class TestPortalPreviewExport(unittest.TestCase):
    def setUp(self):
        self.out_dir = Path(tempfile.mkdtemp(dir=REPO_ROOT / "tmp")) / "portal-preview"

    def test_preview_export_writes_all_pages_under_tmp_only(self):
        result = subprocess.run(
            ["python3", "bin/portal_preview_export.py", "--out-dir", str(self.out_dir)],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        names = {
            "home.html",
            "plans.html",
            "dashboard.html",
            "subscription.html",
            "branded-placeholder.html",
            "help.html",
            "unavailable.html",
            "degraded.html",
            "expired.html",
            "not-found.html",
        }
        self.assertEqual(names, {p.name for p in self.out_dir.glob("*.html")})
        self.assertIn("home", result.stdout)
        self.assertNotIn("portal-sample", result.stdout)
        for path in self.out_dir.glob("*.html"):
            self.assertIn(str(REPO_ROOT / "tmp"), str(path.resolve()))
            html = path.read_text(encoding="utf-8")
            self.assertIn("<!doctype html>", html)
            for needle in FORBIDDEN_PAGE_NEEDLES:
                self.assertNotIn(needle, html)
            self.assertIsNone(
                re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", html, re.I)
            )

    def test_preview_export_refuses_outside_tmp(self):
        result = subprocess.run(
            ["python3", "bin/portal_preview_export.py", "--out-dir", "/tmp/unseen-outside-preview"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing to write outside", result.stderr)

    def test_render_dry_run_refuses_outside_tmp_file(self):
        result = subprocess.run(
            ["python3", "bin/portal_render_dry_run.py", "--page", "home", "--out", "/tmp/outside.html"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing to write outside", result.stderr)


if __name__ == "__main__":
    unittest.main()

import os
import tempfile
import unittest

from _helper import fresh_db
from backend import provisioning_plan as pplan, units


class TestProvisioningPlan(unittest.TestCase):
    def setUp(self):
        self.conn = fresh_db(os.path.join(tempfile.mkdtemp(), "t.sqlite3"))

    def tearDown(self):
        self.conn.close()

    def test_unknown_plan_rejected(self):
        with self.assertRaises(pplan.UnknownPlanError):
            pplan.build_plan(self.conn, "NOPE")

    def test_entitlements_de_us_sg(self):
        # BASIC/CORE exclude SG; PRO/MAX include SG (premium-only)
        basic = pplan.build_plan(self.conn, "BASIC_1M")
        self.assertEqual(basic.regions, ["de"])
        self.assertNotIn("sg", basic.regions)
        self.assertEqual(basic.premium_regions, [])

        core = pplan.build_plan(self.conn, "CORE_1M")
        self.assertNotIn("sg", core.regions)

        pro = pplan.build_plan(self.conn, "PRO_3M")
        self.assertIn("sg", pro.regions)
        self.assertIn("sg", pro.premium_regions)
        maxp = pplan.build_plan(self.conn, "MAX_6M")
        self.assertIn("sg", maxp.regions)

    def test_fast_label_rule_preserved(self):
        basic = pplan.build_plan(self.conn, "BASIC_1M")     # one fast tier -> "Fast"
        self.assertEqual(basic.profile_labels.get("FAST1"), "Fast")
        self.assertNotIn("FAST2", basic.profile_labels)
        self.assertEqual(basic.profile_labels.get("SECURE"), "Secure")
        plus = pplan.build_plan(self.conn, "PLUS_3M")        # both -> Fast1/Fast2
        self.assertEqual(plus.profile_labels.get("FAST1"), "Fast1")
        self.assertEqual(plus.profile_labels.get("FAST2"), "Fast2")

    def test_gib_to_gb_in_plan(self):
        trial = pplan.build_plan(self.conn, "TRIAL")          # 10 GiB
        self.assertEqual(trial.quota_gib, 10)
        self.assertEqual(trial.quota_gb, units.gib_to_gb(10))  # 10.74
        self.assertNotEqual(trial.quota_gb, 10)

    def test_de1_candidate_is_test_status(self):
        plan = pplan.build_plan(self.conn, "TRIAL", preferred_node="de1")
        de1 = next(n for n in plan.candidate_nodes if n.node_code == "de1")
        self.assertEqual(de1.status, "test")
        self.assertTrue(de1.usable_for_dry_run)
        self.assertFalse(de1.usable_for_live)

    def test_live_blocked_by_status_and_phase(self):
        plan = pplan.build_plan(self.conn, "TRIAL", preferred_node="de1")
        self.assertFalse(plan.live_allowed)
        self.assertIn("phase4c_live_disabled", plan.live_blockers)
        self.assertIn("node_not_live:test", plan.live_blockers)
        # Phase 9: the leaked-key blocker was cleared by the fresh de1 rebuild; live stays
        # blocked by the Phase 4C gate + de1 status=test.
        self.assertNotIn("leaked_key_rebuild_pending", plan.live_blockers)

    def test_sanitized_summary_has_no_secrets(self):
        plan = pplan.build_plan(self.conn, "PRO_3M", preferred_node="de1")
        s = str(plan.sanitized_summary()) + str(pplan.hiddify_mutation_plan(plan, "UP0001"))
        for needle in ("Hiddify-API-Key", "api_key", "uuid", "vless://", "ss://", "hy2://",
                       "BEGIN", "/api/v2/admin", "admin_proxy"):
            self.assertNotIn(needle, s)

    def test_hiddify_mutation_plan_uses_relative_path_and_gb(self):
        plan = pplan.build_plan(self.conn, "TRIAL")
        m = pplan.hiddify_mutation_plan(plan, "UP0001")
        self.assertEqual(m["method"], "POST")
        self.assertEqual(m["path"], "/user/")              # relative; no host/secret path
        self.assertEqual(m["usage_limit_GB"], units.gib_to_gb(10))
        self.assertNotIn("uuid", {k.lower() for k in m})


if __name__ == "__main__":
    unittest.main()

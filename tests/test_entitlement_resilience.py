import os
import tempfile
import unittest

from _helper import fresh_db
from backend import (
    availability, entitlements, node_resilience as nr, provisioning_plan, telegram_messages as msg,
)


def _add_node(conn, code, region, status):
    conn.execute("INSERT OR IGNORE INTO proxy_nodes(node_code,region_code,status) VALUES (?,?,?)",
                 (code, region, status))
    conn.commit()


def _open_alert(conn, code, level):
    conn.execute("INSERT INTO node_alerts(node_code,level,metric) VALUES (?,?, 'reachability')",
                 (code, level))
    conn.commit()


class TestEntitlements(unittest.TestCase):
    def setUp(self):
        self.conn = fresh_db(os.path.join(tempfile.mkdtemp(), "t.sqlite3"))

    def tearDown(self):
        self.conn.close()

    def test_region_entitlements_by_plan(self):
        self.assertEqual(entitlements.resolve(self.conn, "TRIAL").regions, ["de"])
        self.assertEqual(entitlements.resolve(self.conn, "BASIC_1M").regions, ["de"])
        self.assertEqual(set(entitlements.resolve(self.conn, "CORE_1M").regions), {"de", "us"})
        self.assertEqual(set(entitlements.resolve(self.conn, "PLUS_3M").regions), {"de", "us"})
        self.assertEqual(set(entitlements.resolve(self.conn, "PRO_3M").regions), {"de", "us", "sg"})
        self.assertEqual(set(entitlements.resolve(self.conn, "MAX_6M").regions), {"de", "us", "sg"})

    def test_sg_premium_only_pro_max(self):
        for plan in ("TRIAL", "BASIC_1M", "CORE_1M", "PLUS_3M"):
            self.assertNotIn("sg", entitlements.resolve(self.conn, plan).regions, plan)
        for plan in ("PRO_3M", "MAX_6M"):
            e = entitlements.resolve(self.conn, plan)
            self.assertIn("sg", e.regions)
            self.assertIn("sg", e.premium_regions)

    def test_default_region_is_de(self):
        self.assertEqual(entitlements.resolve(self.conn, "PRO_3M").default_region, "de")

    def test_fast_label_rule(self):
        self.assertEqual(entitlements.resolve(self.conn, "BASIC_1M").profile_labels.get("FAST1"), "Fast")
        self.assertNotIn("FAST2", entitlements.resolve(self.conn, "BASIC_1M").profile_labels)
        plus = entitlements.resolve(self.conn, "PLUS_3M").profile_labels
        self.assertEqual(plus.get("FAST1"), "Fast1")
        self.assertEqual(plus.get("FAST2"), "Fast2")
        self.assertEqual(plus.get("SECURE"), "Secure")

    def test_unknown_and_disabled_plan_safe(self):
        with self.assertRaises(entitlements.UnknownPlanError):
            entitlements.resolve(self.conn, "NOPE")
        self.conn.execute("UPDATE plans SET is_enabled=0 WHERE plan_code='BASIC_1M'")
        self.conn.commit()
        with self.assertRaises(entitlements.DisabledPlanError):
            entitlements.resolve(self.conn, "BASIC_1M")


class TestNodeReadiness(unittest.TestCase):
    def setUp(self):
        self.conn = fresh_db(os.path.join(tempfile.mkdtemp(), "t.sqlite3"))

    def tearDown(self):
        self.conn.close()

    def test_de1_test_blocks_live_with_reasons(self):
        r = nr.node_readiness(self.conn, "de1", "de", "test")
        self.assertFalse(r.live_ready)
        self.assertIn(nr.NODE_NOT_LIVE, r.reasons)
        self.assertIn(nr.NODE_STATUS_TEST, r.reasons)
        # Phase 9: leaked-key blocker cleared by fresh rebuild; remaining blocker is the
        # real-device protocol connect PASS (data-driven, seeded).
        self.assertIn(nr.REALDEVICE_PROTOCOL_TEST_PENDING, r.reasons)
        self.assertNotIn(nr.LEAKED_KEY_REBUILD_PENDING, r.reasons)
        self.assertTrue(r.dry_run_candidate)                       # test node usable for dry-run

    def test_live_healthy_node_is_live_ready(self):
        _add_node(self.conn, "us1", "us", "live")
        r = nr.node_readiness(self.conn, "us1", "us", "live")
        self.assertTrue(r.live_ready)
        self.assertEqual(r.reasons, [])

    def test_down_node_not_ready(self):
        _add_node(self.conn, "us1", "us", "live")
        _open_alert(self.conn, "us1", "DOWN")
        r = nr.node_readiness(self.conn, "us1", "us", "live")
        self.assertFalse(r.live_ready)
        self.assertFalse(r.dry_run_candidate)         # down → dropped even from dry-run
        self.assertIn(nr.NODE_DOWN, r.reasons)
        self.assertEqual(nr.node_health(self.conn, "us1"), nr.HEALTH_DOWN)

    def test_degraded_node_still_candidate(self):
        _add_node(self.conn, "us1", "us", "live")
        _open_alert(self.conn, "us1", "WARN")
        r = nr.node_readiness(self.conn, "us1", "us", "live")
        self.assertEqual(r.health, nr.HEALTH_DEGRADED)
        self.assertTrue(r.dry_run_candidate)
        self.assertIn(nr.NODE_DEGRADED, r.reasons)
        self.assertFalse(r.live_ready)               # degraded has an open reason → not live

    def test_planned_and_retired_excluded_from_candidates(self):
        _add_node(self.conn, "us9", "us", "planned")
        _add_node(self.conn, "us8", "us", "retired")
        self.assertFalse(nr.node_readiness(self.conn, "us9", "us", "planned").dry_run_candidate)
        self.assertFalse(nr.node_readiness(self.conn, "us8", "us", "retired").live_ready)
        self.assertIn(nr.NODE_STATUS_PLANNED, nr.node_readiness(self.conn, "us9", "us", "planned").reasons)
        self.assertIn(nr.NODE_STATUS_RETIRED, nr.node_readiness(self.conn, "us8", "us", "retired").reasons)

    def test_node_protocol_availability_default_and_explicit(self):
        # absent row → available; explicit is_available=0 → unavailable
        self.assertTrue(nr.node_protocol_available(self.conn, "de1", "FAST1"))
        self.conn.execute("INSERT INTO proxy_node_protocols(node_code,profile_code,is_available) "
                          "VALUES ('de1','FAST2',0)")
        self.conn.commit()
        self.assertFalse(nr.node_protocol_available(self.conn, "de1", "FAST2"))


class TestAvailability(unittest.TestCase):
    def setUp(self):
        self.conn = fresh_db(os.path.join(tempfile.mkdtemp(), "t.sqlite3"))

    def tearDown(self):
        self.conn.close()

    def test_dry_run_de_available_via_test_node(self):
        av = availability.resolve(self.conn, "BASIC_1M", mode=availability.MODE_DRY_RUN)
        self.assertIn("de", av.available_regions)
        # entitlement vs availability are distinct: BASIC is not entitled to SG/US at all
        self.assertEqual(av.entitled_regions, ["de"])

    def test_live_blocked_for_de1_test(self):
        av = availability.resolve(self.conn, "BASIC_1M", mode=availability.MODE_LIVE)
        self.assertNotIn("de", av.available_regions)
        de = av.regions["de"]
        self.assertIn(nr.NODE_STATUS_TEST, de["reasons"])
        # Phase 9: leaked-key blocker cleared; de1 still blocked live via status=test +
        # the remaining real-device protocol-test requirement.
        self.assertIn(nr.REALDEVICE_PROTOCOL_TEST_PENDING, de["reasons"])
        self.assertNotIn(nr.LEAKED_KEY_REBUILD_PENDING, de["reasons"])

    def test_graceful_degradation_other_regions_serve(self):
        # PRO_3M entitled to de+us+sg. Add a healthy live US node and a DOWN live SG node.
        _add_node(self.conn, "us1", "us", "live")
        _add_node(self.conn, "sg1", "sg", "live")
        _open_alert(self.conn, "sg1", "DOWN")
        av = availability.resolve(self.conn, "PRO_3M", mode=availability.MODE_LIVE)
        self.assertIn("us", av.available_regions)                 # healthy live US serves
        unavail = {u["region"] for u in av.unavailable_regions}
        self.assertIn("de", unavail)                              # de1 test
        self.assertIn("sg", unavail)                              # sg1 down
        sg = av.regions["sg"]
        self.assertIn(nr.NODE_DOWN, sg["reasons"])

    def test_all_nodes_down_region_unavailable(self):
        _add_node(self.conn, "us1", "us", "live")
        _open_alert(self.conn, "us1", "DOWN")
        av = availability.resolve(self.conn, "CORE_1M", mode=availability.MODE_LIVE)
        self.assertNotIn("us", av.available_regions)
        self.assertIn(nr.NODE_DOWN, av.regions["us"]["reasons"])

    def test_no_node_region_no_candidate(self):
        av = availability.resolve(self.conn, "CORE_1M", mode=availability.MODE_DRY_RUN)
        # CORE entitled to de+us; us has no node → no_candidate_node
        self.assertIn("us", {u["region"] for u in av.unavailable_regions})
        self.assertIn(nr.NO_CANDIDATE_NODE, av.regions["us"]["reasons"])

    def test_disabled_protocol_marked_unavailable_in_region(self):
        # mark FAST2 down on de1 → for a plan with both fast tiers, FAST2 unavailable in DE (dry-run)
        self.conn.execute("INSERT INTO proxy_node_protocols(node_code,profile_code,is_available) "
                          "VALUES ('de1','FAST2',0)")
        self.conn.commit()
        av = availability.resolve(self.conn, "PLUS_3M", mode=availability.MODE_DRY_RUN)
        de_protocols = {p["profile_code"]: p for p in av.regions["de"]["protocols"]}
        self.assertFalse(de_protocols["FAST2"]["available"])
        self.assertIn(nr.PROTOCOL_MISSING, de_protocols["FAST2"]["reasons"])
        self.assertTrue(de_protocols["FAST1"]["available"])      # FAST1 still up

    def test_disabled_region_status_marks_unavailable(self):
        # A region with no test/standby/live node (e.g. status planned + no node) is unavailable.
        av = availability.resolve(self.conn, "PRO_3M", mode=availability.MODE_DRY_RUN)
        self.assertIn("sg", {u["region"] for u in av.unavailable_regions})  # sg planned, no node

    def test_sg_unavailability_does_not_affect_basic_core(self):
        # BASIC/CORE aren't entitled to SG, so SG being absent never appears for them.
        for plan in ("BASIC_1M", "CORE_1M"):
            av = availability.resolve(self.conn, plan, mode=availability.MODE_DRY_RUN)
            self.assertNotIn("sg", av.entitled_regions)
            self.assertNotIn("sg", {u["region"] for u in av.unavailable_regions})


class TestProvisioningPlanIntegration(unittest.TestCase):
    def setUp(self):
        self.conn = fresh_db(os.path.join(tempfile.mkdtemp(), "t.sqlite3"))

    def tearDown(self):
        self.conn.close()

    def test_plan_uses_resolver_fields(self):
        plan = provisioning_plan.build_plan(self.conn, "PRO_3M", preferred_node="de1")
        self.assertEqual(set(plan.entitled_regions), {"de", "us", "sg"})
        self.assertIn("de", plan.available_regions)            # de1 test = dry-run candidate
        unavail = {u["region"] for u in plan.unavailable_regions}
        self.assertIn("us", unavail)
        self.assertIn("sg", unavail)
        # existing live_blockers preserved (Phase 4C contract); leaked-key cleared in Phase 9
        self.assertIn("phase4c_live_disabled", plan.live_blockers)
        self.assertNotIn("leaked_key_rebuild_pending", plan.live_blockers)
        self.assertIn("node_not_live:test", plan.live_blockers)
        # node_readiness present + sanitized
        self.assertTrue(any(n["node_code"] == "de1" for n in plan.node_readiness))

    def test_summary_has_no_secrets(self):
        plan = provisioning_plan.build_plan(self.conn, "PRO_3M", preferred_node="de1")
        blob = str(plan.sanitized_summary())
        for needle in ("Hiddify-API-Key", "vless://", "ss://", "hy2://", "5.249.160.59",
                       "/api/v2/admin", "uuid"):
            self.assertNotIn(needle, blob)


class TestCustomerMessages(unittest.TestCase):
    def test_availability_messages_have_no_secrets_or_ip(self):
        samples = [msg.region_available("de"), msg.region_unavailable("sg"),
                   msg.region_test_only("de"), msg.protocol_unavailable("de", "Fast1"),
                   msg.plan_excludes_region("sg")]
        for s in samples:
            for needle in ("5.249.160.59", "node-de.unseen.click", "Hiddify-API-Key",
                           "vless://", "ss://", "hy2://", "uuid", "/api/v2/", "token"):
                self.assertNotIn(needle, s)
        # Burmese present
        self.assertTrue(any("က" <= ch <= "႟" for ch in msg.region_unavailable("de")))


if __name__ == "__main__":
    unittest.main()

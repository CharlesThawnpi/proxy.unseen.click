import os
import tempfile
import unittest

from _helper import fresh_db
from backend import display, seed


class TestSeed(unittest.TestCase):
    def setUp(self):
        self.tmp = os.path.join(tempfile.mkdtemp(), "t.sqlite3")
        self.conn = fresh_db(self.tmp)

    def tearDown(self):
        self.conn.close()

    def test_plan_values_match_authoritative(self):
        want = {
            "TRIAL":    (10, 7, 0),
            "BASIC_1M": (50, 30, 3000),
            "CORE_1M":  (100, 30, 5000),
            "PLUS_3M":  (360, 90, 15000),
            "PRO_3M":   (600, 90, 20000),
            "MAX_6M":   (1500, 180, 30000),
        }
        for code, (gib, days, price) in want.items():
            row = self.conn.execute(
                "SELECT data_limit_gib,duration_days,price_mmk FROM plans WHERE plan_code=?",
                (code,)).fetchone()
            self.assertIsNotNone(row, code)
            self.assertEqual((row[0], row[1], row[2]), (gib, days, price), code)

    def test_idempotent_seed(self):
        before = self.conn.execute("SELECT COUNT(*) FROM plans").fetchone()[0]
        seed.seed(self.conn)  # run again
        after = self.conn.execute("SELECT COUNT(*) FROM plans").fetchone()[0]
        self.assertEqual(before, after)

    def test_de1_is_test_not_live(self):
        row = self.conn.execute(
            "SELECT status,is_master_colocated FROM proxy_nodes WHERE node_code='de1'").fetchone()
        self.assertEqual(row["status"], "test")
        self.assertNotEqual(row["status"], "live")
        self.assertEqual(row["is_master_colocated"], 0)  # co-location retired

    def test_de_default_sg_premium(self):
        de = self.conn.execute("SELECT is_default,is_premium_only FROM proxy_regions WHERE region_code='de'").fetchone()
        sg = self.conn.execute("SELECT is_default,is_premium_only FROM proxy_regions WHERE region_code='sg'").fetchone()
        self.assertEqual(de["is_default"], 1)
        self.assertEqual(sg["is_premium_only"], 1)

    def test_sg_not_in_basic_or_core(self):
        for plan in ("TRIAL", "BASIC_1M", "CORE_1M"):
            self.assertNotIn("sg", seed.entitled_regions(self.conn, plan), plan)
        for plan in ("PRO_3M", "MAX_6M"):
            self.assertIn("sg", seed.entitled_regions(self.conn, plan), plan)

    def test_fast_label_rule(self):
        # one fast tier -> "Fast"
        basic = seed.entitled_profiles(self.conn, "BASIC_1M")
        labels_basic = display.fast_labels(basic)
        self.assertEqual(labels_basic.get("FAST1"), "Fast")
        self.assertNotIn("FAST2", labels_basic)
        self.assertEqual(labels_basic.get("SECURE"), "Secure")
        # both fast tiers -> Fast1 / Fast2
        plus = seed.entitled_profiles(self.conn, "PLUS_3M")
        labels_plus = display.fast_labels(plus)
        self.assertEqual(labels_plus.get("FAST1"), "Fast1")
        self.assertEqual(labels_plus.get("FAST2"), "Fast2")
        self.assertEqual(labels_plus.get("SECURE"), "Secure")


if __name__ == "__main__":
    unittest.main()

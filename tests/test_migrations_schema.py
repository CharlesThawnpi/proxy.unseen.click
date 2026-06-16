import os
import tempfile
import unittest

from _helper import REPO_ROOT  # noqa: F401  (ensures sys.path)
from backend import migrate, db as dbmod


class TestMigrations(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = os.path.join(self.tmp, "t.sqlite3")

    def test_apply_clean_then_idempotent(self):
        first = migrate.migrate_path(self.db)
        self.assertIn("0001_initial", first)
        # re-run: nothing new applied
        second = migrate.migrate_path(self.db)
        self.assertEqual(second, [])

    def test_integrity_and_fk(self):
        migrate.migrate_path(self.db)
        conn = dbmod.connect(self.db)
        self.assertTrue(dbmod.integrity_ok(conn))
        self.assertEqual(dbmod.foreign_key_violations(conn), [])
        # spot-check a few required tables exist
        names = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        for t in ("schema_migrations", "customers", "platform_accounts", "plans",
                  "proxy_regions", "proxy_nodes", "protocol_profiles",
                  "plan_region_entitlements", "plan_protocol_entitlements",
                  "subscriptions", "access_profiles", "payment_orders",
                  "idempotency_keys", "outbound_messages", "referral_credits",
                  "node_metrics", "node_alerts", "audit_logs", "settings"):
            self.assertIn(t, names, f"missing table {t}")
        conn.close()

    def test_foreign_keys_enforced(self):
        migrate.migrate_path(self.db)
        conn = dbmod.connect(self.db)
        with self.assertRaises(Exception):
            # platform_accounts.customer_id has a NOT NULL FK -> must fail for unknown customer
            conn.execute(
                "INSERT INTO platform_accounts(platform_name,platform_user_id,customer_id)"
                " VALUES ('telegram','x',99999)")
            conn.commit()
        conn.close()


if __name__ == "__main__":
    unittest.main()

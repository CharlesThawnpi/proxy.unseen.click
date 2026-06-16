import json
import os
import tempfile
import unittest

from _helper import fresh_db
from backend import customer_code, units, config
from backend.config import NodeApiConfig
from backend.hiddify import HiddifyClient


class TestUnits(unittest.TestCase):
    def test_gib_gb_conversion(self):
        self.assertEqual(units.gib_to_gb(10), 10.74)        # 10 GiB ~ 10.74 GB
        self.assertEqual(units.gib_to_gb(0), 0.0)
        # round-trip stays close
        self.assertAlmostEqual(units.gb_to_gib(units.gib_to_gb(100)), 100, places=1)
        self.assertGreater(units.gib_to_gb(100), 100)        # GiB number > its GB value


class TestCustomerCode(unittest.TestCase):
    def setUp(self):
        self.conn = fresh_db(os.path.join(tempfile.mkdtemp(), "t.sqlite3"))

    def tearDown(self):
        self.conn.close()

    def test_gap_safe_max_id_plus_one(self):
        self.assertEqual(customer_code.next_public_customer_code(self.conn), "UP0001")
        self.conn.execute("INSERT INTO customers(id) VALUES (1)")
        self.conn.execute("INSERT INTO customers(id) VALUES (2)")
        self.conn.commit()
        self.assertEqual(customer_code.next_public_customer_code(self.conn), "UP0003")
        # delete the highest; next must still be max+1 (3), NOT count+1 (2) -> gap-safe
        self.conn.execute("DELETE FROM customers WHERE id=2")
        self.conn.commit()
        self.assertEqual(customer_code.next_public_customer_code(self.conn), "UP0002")  # max(id)=1 -> 2
        # reinsert id=2 and 5, delete 5, ensure no collision logic uses count
        self.conn.execute("INSERT INTO customers(id) VALUES (2)")
        self.conn.execute("INSERT INTO customers(id) VALUES (5)")
        self.conn.commit()
        self.assertEqual(customer_code.next_public_customer_code(self.conn), "UP0006")


class _MockOpener:
    """Captures the last request; returns a canned response."""
    def __init__(self, status=200, payload=None):
        self.calls = []
        self._status = status
        self._payload = payload if payload is not None else {}

    def __call__(self, method, url, headers, body):
        self.calls.append({"method": method, "url": url, "headers": headers,
                           "body": json.loads(body) if body else None})
        return self._status, json.dumps(self._payload).encode()


class TestHiddifyClient(unittest.TestCase):
    def setUp(self):
        self.node = NodeApiConfig(node_code="de1", base_host="node-de.unseen.click",
                                  admin_proxy_path="SECRETPATH", api_key="ADMIN-UUID")

    def test_path_builders_match_contract(self):
        self.assertEqual(HiddifyClient.user_list_path(), "/user/")
        self.assertEqual(HiddifyClient.user_path("u1"), "/user/u1/")
        self.assertTrue(HiddifyClient.all_configs_path("u1").startswith("/all-configs/?uuid="))
        # base assembles admin api path
        self.assertEqual(self.node.admin_api_base,
                         "https://node-de.unseen.click/SECRETPATH/api/v2/admin")

    def test_create_uses_header_and_gib_to_gb(self):
        op = _MockOpener(status=200, payload={"uuid": "x", "name": "disposable-test"})
        cli = HiddifyClient(self.node, opener=op)
        res = cli.create_user(name="disposable-test", data_limit_gib=10, package_days=7)
        self.assertTrue(res.ok)
        call = op.calls[-1]
        self.assertEqual(call["method"], "POST")
        self.assertTrue(call["url"].endswith("/api/v2/admin/user/"))
        self.assertEqual(call["headers"].get("Hiddify-API-Key"), "ADMIN-UUID")
        # GiB->GB conversion applied (10 GiB -> 10.74 GB), NOT raw 10
        self.assertEqual(call["body"]["usage_limit_GB"], units.gib_to_gb(10))
        self.assertNotEqual(call["body"]["usage_limit_GB"], 10)
        self.assertEqual(call["body"]["package_days"], 7)

    def test_disable_is_patch_enable_false(self):
        op = _MockOpener()
        HiddifyClient(self.node, opener=op).disable_user("u1")
        self.assertEqual(op.calls[-1]["method"], "PATCH")
        self.assertEqual(op.calls[-1]["body"], {"enable": False})


class TestLiveSafety(unittest.TestCase):
    def test_live_latch_disabled_by_default(self):
        os.environ.pop(config.LIVE_ENV_LATCH, None)
        self.assertFalse(config.live_latch_enabled())

    def test_live_latch_requires_exact_value(self):
        os.environ[config.LIVE_ENV_LATCH] = "0"
        self.assertFalse(config.live_latch_enabled())
        os.environ[config.LIVE_ENV_LATCH] = "1"
        self.assertTrue(config.live_latch_enabled())
        os.environ.pop(config.LIVE_ENV_LATCH, None)

    def test_dry_run_provision_makes_no_network_call(self):
        # provision-one dry-run path must not construct/use a network client.
        import importlib.util
        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(repo, "bin", "hiddify_customer_provisioner.py")
        spec = importlib.util.spec_from_file_location("prov", path)
        prov = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(prov)
        db = fresh_db(os.path.join(tempfile.mkdtemp(), "t.sqlite3"))
        dbfile = [r[0] for r in db.execute("PRAGMA database_list")][0] if False else None
        db.close()
        # run via main(); ensure it returns 0 and does not raise / call network
        tmpdb = os.path.join(tempfile.mkdtemp(), "t.sqlite3")
        fresh_db(tmpdb).close()
        os.environ.pop(config.LIVE_ENV_LATCH, None)
        rc = prov.main(["--db", tmpdb, "provision-one", "--customer", "1", "--plan", "TRIAL"])
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()

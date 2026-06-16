import os
import tempfile
import unittest

from _helper import fresh_db
from backend import account_service as acct


class TestAccountService(unittest.TestCase):
    def setUp(self):
        self.conn = fresh_db(os.path.join(tempfile.mkdtemp(), "t.sqlite3"))

    def tearDown(self):
        self.conn.close()

    def test_creates_customer_and_platform_account(self):
        cid = acct.resolve_customer(self.conn, "telegram", "111")
        self.assertIsInstance(cid, int)
        # platform_accounts row exists, mapped to this customer
        row = self.conn.execute(
            "SELECT customer_id FROM platform_accounts WHERE platform_name='telegram' AND platform_user_id='111'"
        ).fetchone()
        self.assertEqual(int(row[0]), cid)
        # customer row exists with a public code (gap-safe = its own id)
        self.assertEqual(acct.public_code(self.conn, cid), "UP0001")
        # preferred_language defaults to Burmese
        lang = self.conn.execute("SELECT preferred_language FROM customers WHERE id=?", (cid,)).fetchone()[0]
        self.assertEqual(lang, "my")

    def test_resolve_is_idempotent(self):
        cid1 = acct.resolve_customer(self.conn, "telegram", "111")
        cid2 = acct.resolve_customer(self.conn, "telegram", "111")
        self.assertEqual(cid1, cid2)
        # exactly one customer and one platform account were created
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0], 1)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM platform_accounts").fetchone()[0], 1)

    def test_public_code_gap_safe(self):
        a = acct.resolve_customer(self.conn, "telegram", "1")
        b = acct.resolve_customer(self.conn, "messenger", "2")
        self.assertEqual(acct.public_code(self.conn, a), "UP0001")
        self.assertEqual(acct.public_code(self.conn, b), "UP0002")
        # delete the latest; a new customer still gets a NON-colliding code (max-id+1 semantics)
        self.conn.execute("DELETE FROM customers WHERE id=?", (b,))
        self.conn.commit()
        c = acct.resolve_customer(self.conn, "viber", "3")
        self.assertEqual(acct.public_code(self.conn, c), "UP0003")
        self.assertNotEqual(acct.public_code(self.conn, c), acct.public_code(self.conn, a))

    def test_invalid_platform_rejected(self):
        with self.assertRaises(acct.UnknownPlatformError):
            acct.resolve_customer(self.conn, "signal", "x")
        # nothing was created
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0], 0)

    def test_all_allowed_platforms_accepted(self):
        for i, p in enumerate(("telegram", "messenger", "viber", "whatsapp", "web")):
            cid = acct.resolve_customer(self.conn, p, str(i))
            self.assertIsInstance(cid, int)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0], 5)


if __name__ == "__main__":
    unittest.main()

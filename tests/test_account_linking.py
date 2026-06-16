import os
import tempfile
import unittest

from _helper import fresh_db
from backend import account_linking as link, account_service as acct


class TestAccountLinking(unittest.TestCase):
    def setUp(self):
        self.conn = fresh_db(os.path.join(tempfile.mkdtemp(), "t.sqlite3"))
        self.cid = acct.resolve_customer(self.conn, "telegram", "owner-1")

    def tearDown(self):
        self.conn.close()

    def test_issue_stores_hash_not_raw(self):
        raw = link.issue_link_code(self.conn, self.cid)
        self.assertTrue(6 <= len(raw) <= 8)
        stored = self.conn.execute(
            "SELECT code_hash FROM account_link_tokens WHERE customer_id=?", (self.cid,)
        ).fetchall()
        self.assertEqual(len(stored), 1)
        # the raw code is NOT present anywhere in the stored hash
        self.assertNotIn(raw.upper(), stored[0][0])
        self.assertNotEqual(stored[0][0], raw)
        self.assertEqual(len(stored[0][0]), 64)  # sha256 hex

    def test_validate_then_consume_links_new_platform(self):
        raw = link.issue_link_code(self.conn, self.cid)
        v = link.validate_link_code(self.conn, raw)
        self.assertTrue(v.valid)
        self.assertEqual(v.customer_id, self.cid)
        res = link.consume_link_code(self.conn, raw, ("messenger", "msgr-1"))
        self.assertEqual(res.status, "linked")
        # messenger account now maps to the same customer
        self.assertEqual(acct.find_customer(self.conn, "messenger", "msgr-1"), self.cid)

    def test_one_time_use_then_invalid(self):
        raw = link.issue_link_code(self.conn, self.cid)
        link.consume_link_code(self.conn, raw, ("messenger", "msgr-1"))
        # re-using the same code is now reason-opaque invalid (consumed)
        again = link.consume_link_code(self.conn, raw, ("viber", "viber-1"))
        self.assertEqual(again.status, "invalid")
        self.assertFalse(link.validate_link_code(self.conn, raw).valid)

    def test_expired_code_is_invalid(self):
        raw = link.issue_link_code(self.conn, self.cid)
        # force-expire the token
        self.conn.execute(
            "UPDATE account_link_tokens SET expires_at=datetime('now','-1 hour') WHERE customer_id=?",
            (self.cid,))
        self.conn.commit()
        self.assertFalse(link.validate_link_code(self.conn, raw).valid)
        self.assertEqual(link.consume_link_code(self.conn, raw, ("viber", "v1")).status, "invalid")

    def test_reason_opaque_invalid_has_no_reason(self):
        v = link.validate_link_code(self.conn, "NOSUCHCODE")
        self.assertFalse(v.valid)
        self.assertIsNone(v.customer_id)
        # the result object carries no field distinguishing unknown/expired/used
        self.assertEqual(set(v.__dataclass_fields__), {"valid", "customer_id"})

    def test_already_linked_is_idempotent_noop(self):
        # first link messenger->owner
        raw1 = link.issue_link_code(self.conn, self.cid)
        self.assertEqual(link.consume_link_code(self.conn, raw1, ("messenger", "msgr-1")).status, "linked")
        # re-linking the SAME pair with a fresh code is a friendly idempotent no-op
        raw2 = link.issue_link_code(self.conn, self.cid)
        r = link.consume_link_code(self.conn, raw2, ("messenger", "msgr-1"))
        self.assertEqual(r.status, "already_linked")
        self.assertEqual(r.customer_id, self.cid)
        # still exactly one messenger mapping
        self.assertEqual(self.conn.execute(
            "SELECT COUNT(*) FROM platform_accounts WHERE platform_name='messenger' AND platform_user_id='msgr-1'"
        ).fetchone()[0], 1)

    def test_merge_path_is_dry_run_no_mutation(self):
        other = acct.resolve_customer(self.conn, "messenger", "msgr-9")
        before_customers = self.conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
        before_merges = self.conn.execute("SELECT COUNT(*) FROM customer_merges").fetchone()[0]
        raw = link.issue_link_code(self.conn, self.cid)
        res = link.consume_link_code(self.conn, raw, ("messenger", "msgr-9"))
        self.assertEqual(res.status, "merge_required_dry_run")
        # NO mutation: other still maps to itself, no merged_into set, no customer_merges row,
        # and the code was NOT consumed (still valid for a future, real merge)
        self.assertEqual(acct.find_customer(self.conn, "messenger", "msgr-9"), other)
        self.assertIsNone(self.conn.execute(
            "SELECT merged_into_customer_id FROM customers WHERE id=?", (other,)).fetchone()[0])
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0], before_customers)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM customer_merges").fetchone()[0], before_merges)
        self.assertTrue(link.validate_link_code(self.conn, raw).valid)


if __name__ == "__main__":
    unittest.main()

import os
import tempfile
import unittest

from _helper import fresh_db
from backend import idempotency as idem, payment_flow


class TestIdempotency(unittest.TestCase):
    def setUp(self):
        self.conn = fresh_db(os.path.join(tempfile.mkdtemp(), "t.sqlite3"))

    def tearDown(self):
        self.conn.close()

    def test_begin_then_complete_then_duplicate(self):
        first = idem.begin_idempotent(self.conn, "payment_approval", "k1")
        self.assertEqual(first.state, idem.STATE_STARTED)
        self.assertTrue(first.should_proceed)
        idem.complete_idempotent(self.conn, "payment_approval", "k1", "result:abc")
        # duplicate begin after completion returns the prior result
        dup = idem.begin_idempotent(self.conn, "payment_approval", "k1")
        self.assertEqual(dup.state, idem.STATE_ALREADY_COMPLETED)
        self.assertEqual(dup.result_ref, "result:abc")
        self.assertFalse(dup.should_proceed)

    def test_in_progress_duplicate_refuses(self):
        idem.begin_idempotent(self.conn, "provision_subscription", "k2")
        dup = idem.begin_idempotent(self.conn, "provision_subscription", "k2")
        self.assertEqual(dup.state, idem.STATE_IN_PROGRESS)
        self.assertFalse(dup.should_proceed)

    def test_complete_does_not_overwrite_prior_result(self):
        idem.begin_idempotent(self.conn, "referral_grant", "k3")
        idem.complete_idempotent(self.conn, "referral_grant", "k3", "first")
        again = idem.complete_idempotent(self.conn, "referral_grant", "k3", "second")
        self.assertEqual(again, "first")  # stable replay

    def test_only_one_row_per_scope_key(self):
        idem.begin_idempotent(self.conn, "account_link_merge", "k4")
        idem.begin_idempotent(self.conn, "account_link_merge", "k4")
        idem.complete_idempotent(self.conn, "account_link_merge", "k4", "r")
        n = self.conn.execute(
            "SELECT COUNT(*) FROM idempotency_keys WHERE scope='account_link_merge' AND key='k4'"
        ).fetchone()[0]
        self.assertEqual(n, 1)

    def test_invalid_scope_rejected(self):
        with self.assertRaises(idem.UnknownScopeError):
            idem.begin_idempotent(self.conn, "not_a_scope", "k")

    def test_same_key_different_scope_independent(self):
        a = idem.begin_idempotent(self.conn, "payment_approval", "shared")
        b = idem.begin_idempotent(self.conn, "provision_subscription", "shared")
        self.assertEqual(a.state, idem.STATE_STARTED)
        self.assertEqual(b.state, idem.STATE_STARTED)


class TestPaymentFlowDryRun(unittest.TestCase):
    def setUp(self):
        self.conn = fresh_db(os.path.join(tempfile.mkdtemp(), "t.sqlite3"))

    def tearDown(self):
        self.conn.close()

    def test_approve_payment_no_duplicate(self):
        r1 = payment_flow.approve_payment_dry_run(self.conn, 42)
        self.assertFalse(r1.duplicate)
        r2 = payment_flow.approve_payment_dry_run(self.conn, 42)
        self.assertTrue(r2.duplicate)
        self.assertEqual(r1.result_ref, r2.result_ref)
        # exactly one approval key recorded
        n = self.conn.execute(
            "SELECT COUNT(*) FROM idempotency_keys WHERE scope='payment_approval' AND key='order:42'"
        ).fetchone()[0]
        self.assertEqual(n, 1)

    def test_provision_no_duplicate_and_no_live_call(self):
        r1 = payment_flow.provision_subscription_dry_run(self.conn, 7)
        r2 = payment_flow.provision_subscription_dry_run(self.conn, 7)
        self.assertFalse(r1.duplicate)
        self.assertTrue(r2.duplicate)
        self.assertIn("dry-run", r1.result_ref)
        # provisioning never created a subscription row (boundary only, no live mutation)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM subscriptions").fetchone()[0], 0)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM access_profiles").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()

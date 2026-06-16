import os
import re
import socket
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from _helper import fresh_db
from backend import (
    account_service,
    branded_link_resolver,
    portal_access,
    portal_app,
    portal_auth,
    portal_sessions,
    portal_tokens,
    portal_viewmodels,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


def _sample(conn):
    return portal_viewmodels.sample_data(conn)


class TestPortalTokens(unittest.TestCase):
    def setUp(self):
        self.conn = fresh_db(os.path.join(tempfile.mkdtemp(), "portal_auth.sqlite3"))
        self.sample = _sample(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_opaque_token_shape_and_hash_storage_only(self):
        issued = portal_access.issue_token(
            self.conn,
            customer_id=self.sample["customer_id"],
            subscription_id=self.sample["subscription_id"],
        )
        self.assertGreaterEqual(len(issued.raw_token), 40)
        self.assertRegex(issued.raw_token, r"^[A-Za-z0-9_-]+$")
        self.assertEqual(len(issued.token_hash), 64)
        row = self.conn.execute("SELECT * FROM portal_access_tokens WHERE id=?", (issued.token_id,)).fetchone()
        blob = " ".join(str(v) for v in dict(row).values())
        self.assertIn(issued.token_hash, blob)
        self.assertNotIn(issued.raw_token, blob)

    def test_token_verify_unknown_expired_revoked(self):
        now = datetime(2026, 6, 16, 6, 0, 0)
        issued = portal_access.issue_token(
            self.conn,
            customer_id=self.sample["customer_id"],
            subscription_id=self.sample["subscription_id"],
            now=now,
        )
        self.assertTrue(portal_access.verify_token(self.conn, issued.raw_token, now=now).valid)
        self.assertFalse(portal_access.verify_token(self.conn, "not-a-real-token", now=now).valid)
        self.assertEqual(
            portal_access.verify_token(self.conn, issued.raw_token, now=now + timedelta(hours=2)).reason,
            "expired",
        )
        fresh = portal_access.issue_token(
            self.conn,
            customer_id=self.sample["customer_id"],
            subscription_id=self.sample["subscription_id"],
            now=now,
        )
        portal_access.revoke_token(self.conn, fresh.token_id)
        self.assertEqual(portal_access.verify_token(self.conn, fresh.raw_token, now=now).reason, "revoked")

    def test_constant_time_helper_and_redaction(self):
        raw = portal_tokens.generate_opaque_token()
        handle = portal_tokens.hash_token(raw)
        self.assertTrue(portal_tokens.verify_token_hash(raw, handle))
        self.assertTrue(portal_tokens.constant_time_equal(handle, handle))
        redacted = portal_tokens.redact(raw)
        self.assertNotIn(raw, redacted)
        self.assertIn("token:<redacted:", redacted)

    def test_audit_rows_are_sanitized(self):
        issued = portal_access.issue_token(
            self.conn,
            customer_id=self.sample["customer_id"],
            subscription_id=self.sample["subscription_id"],
        )
        portal_access.verify_token(self.conn, issued.raw_token)
        portal_access.verify_token(self.conn, "unknown-token")
        blob = " ".join(r[0] or "" for r in self.conn.execute("SELECT detail FROM audit_logs").fetchall())
        self.assertNotIn(issued.raw_token, blob)
        self.assertNotRegex(blob, r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


class TestPortalSessions(unittest.TestCase):
    def setUp(self):
        self.conn = fresh_db(os.path.join(tempfile.mkdtemp(), "portal_sessions.sqlite3"))
        self.sample = _sample(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_session_create_verify_expire_revoke_hash_only(self):
        now = datetime(2026, 6, 16, 6, 0, 0)
        created = portal_sessions.create_session(
            self.conn,
            customer_id=self.sample["customer_id"],
            now=now,
        )
        row = self.conn.execute("SELECT * FROM portal_sessions WHERE id=?", (created.session_id,)).fetchone()
        blob = " ".join(str(v) for v in dict(row).values())
        self.assertIn(created.session_hash, blob)
        self.assertNotIn(created.raw_session_id, blob)
        self.assertTrue(portal_sessions.verify_session(self.conn, created.raw_session_id, now=now).valid)
        self.assertEqual(
            portal_sessions.verify_session(self.conn, created.raw_session_id, now=now + timedelta(hours=3)).reason,
            "expired",
        )
        fresh = portal_sessions.create_session(self.conn, customer_id=self.sample["customer_id"], now=now)
        portal_sessions.revoke_session(self.conn, fresh.session_id)
        self.assertEqual(portal_sessions.verify_session(self.conn, fresh.raw_session_id, now=now).reason, "revoked")

    def test_cookie_helper_attributes(self):
        raw = portal_tokens.generate_opaque_token()
        cookie = portal_sessions.build_set_cookie_value(raw, max_age=3600, same_site="Strict")
        self.assertIn("HttpOnly", cookie)
        self.assertIn("Secure", cookie)
        self.assertIn("SameSite=Strict", cookie)
        self.assertIn("Path=/", cookie)
        self.assertIn("Max-Age=3600", cookie)


class TestBrandedResolverAndRoutes(unittest.TestCase):
    def setUp(self):
        self.conn = fresh_db(os.path.join(tempfile.mkdtemp(), "portal_resolver.sqlite3"))
        self.sample = _sample(self.conn)

    def tearDown(self):
        self.conn.close()

    def assertSafe(self, html, raw_values=()):
        for value in raw_values:
            self.assertNotIn(value, html)
        for needle in ("Hiddify-API-Key", "/api/v2/", "vless://", "ss://", "hy2://", "hiddify://",
                       "node-de.unseen.click", "portal-sample"):
            self.assertNotIn(needle, html)
        self.assertIsNone(re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", html, re.I))

    def test_resolver_valid_creates_session_context(self):
        issued = portal_access.issue_token(
            self.conn,
            customer_id=self.sample["customer_id"],
            subscription_id=self.sample["subscription_id"],
        )
        resolved = branded_link_resolver.resolve(self.conn, issued.raw_token)
        self.assertTrue(resolved.valid)
        self.assertTrue(resolved.session_created)
        self.assertEqual(resolved.customer_id, self.sample["customer_id"])
        self.assertEqual(resolved.session_context.customer_id, self.sample["customer_id"])
        sessions = self.conn.execute("SELECT COUNT(*) FROM portal_sessions").fetchone()[0]
        self.assertEqual(sessions, 1)

    def test_route_valid_invalid_and_expired_do_not_leak_token(self):
        now = datetime(2026, 6, 16, 6, 0, 0)
        issued = portal_access.issue_token(
            self.conn,
            customer_id=self.sample["customer_id"],
            subscription_id=self.sample["subscription_id"],
        )
        ok = portal_app.render(self.conn, f"/s/{issued.raw_token}")
        self.assertEqual(ok.status_code, 200)
        code = account_service.public_code(self.conn, self.sample["customer_id"])
        self.assertIn(code, ok.body)
        self.assertSafe(ok.body, (issued.raw_token, issued.token_hash))

        bad = portal_app.render(self.conn, "/s/not-a-real-token")
        self.assertEqual(bad.status_code, 404)
        self.assertNotIn("not-a-real-token", bad.body)
        self.assertSafe(bad.body)

        expired = portal_access.issue_token(
            self.conn,
            customer_id=self.sample["customer_id"],
            subscription_id=self.sample["subscription_id"],
            expires_at="2026-06-16 05:00:00",
            now=now,
        )
        old = portal_app.render(self.conn, f"/s/{expired.raw_token}")
        self.assertEqual(old.status_code, 410)
        self.assertSafe(old.body, (expired.raw_token, expired.token_hash))

    def test_private_pages_accept_session_context_and_block_other_customer(self):
        context = portal_auth.synthetic_context(self.sample["customer_id"])
        dashboard = portal_app.render(self.conn, "/customer/status", session_context=context)
        self.assertEqual(dashboard.status_code, 200)
        other_cid = account_service.resolve_customer(self.conn, "web", "other-sample")
        other_context = portal_auth.synthetic_context(other_cid)
        sub = portal_app.render(
            self.conn,
            f"/subscriptions/{self.sample['subscription_id']}",
            session_context=other_context,
        )
        self.assertEqual(sub.status_code, 404)
        self.assertSafe(sub.body)

    def test_public_pages_do_not_require_auth_or_network(self):
        original_socket = socket.socket

        def fail_socket(*args, **kwargs):
            raise AssertionError("network/server attempted")

        socket.socket = fail_socket
        try:
            for path in ("/", "/plans", "/help"):
                with self.subTest(path=path):
                    res = portal_app.render(self.conn, path)
                    self.assertEqual(res.status_code, 200)
                    self.assertSafe(res.body)
        finally:
            socket.socket = original_socket


class TestPortalAuthCli(unittest.TestCase):
    def test_auth_smoke_and_token_cli_are_sanitized(self):
        for cmd in (["python3", "bin/portal_auth_smoke.py"], ["python3", "bin/portal_token_dry_run.py"]):
            with self.subTest(cmd=cmd):
                result = subprocess.run(cmd, cwd=REPO_ROOT, check=True, text=True, capture_output=True)
                self.assertIn("fingerprint", result.stdout)
                self.assertNotIn("unseen_portal_session=", result.stdout)
                self.assertNotRegex(result.stdout, r"[A-Za-z0-9_-]{40,}")


if __name__ == "__main__":
    unittest.main()

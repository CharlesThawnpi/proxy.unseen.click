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
    access_log,
    portal_access,
    portal_cookies,
    portal_csrf,
    portal_http,
    portal_sessions,
    portal_viewmodels,
    rate_limit,
    sidecar_boundary,
    timezone as tz,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)


def _sample(conn):
    return portal_viewmodels.sample_data(conn)


def _session_cookie_header(conn, customer_id):
    created = portal_sessions.create_session(conn, customer_id=customer_id)
    value = portal_cookies.build_session_set_cookie(created.raw_session_id).split(";", 1)[0]
    return value, created.raw_session_id


class TestHttpRoutingNoNetwork(unittest.TestCase):
    def setUp(self):
        self.conn = fresh_db(os.path.join(tempfile.mkdtemp(), "http_routes.sqlite3"))
        self.sample = _sample(self.conn)
        self.app = portal_http.PortalHttpApp(self.conn)

    def tearDown(self):
        self.conn.close()

    def _get(self, path, cookie=None):
        headers = {"Cookie": cookie} if cookie else {}
        req = portal_http.HttpRequest.build("GET", path, headers=headers, remote_addr="203.0.113.5")
        return self.app.handle(req)

    def test_public_pages_render_without_session_or_network(self):
        original = socket.socket
        socket.socket = lambda *a, **k: (_ for _ in ()).throw(AssertionError("network attempted"))
        try:
            for path in ("/", "/plans", "/help"):
                with self.subTest(path=path):
                    res = self._get(path)
                    self.assertEqual(res.status_code, 200)
                    self.assertEqual(res.content_type, "text/html; charset=utf-8")
                    self.assertEqual(res.headers["X-Frame-Options"], "DENY")
                    self.assertIn("Content-Security-Policy", res.headers)
        finally:
            socket.socket = original

    def test_dashboard_requires_session(self):
        noauth = self._get("/dashboard")
        self.assertEqual(noauth.status_code, 401)
        cookie, _ = _session_cookie_header(self.conn, self.sample["customer_id"])
        ok = self._get("/dashboard", cookie=cookie)
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.headers["Cache-Control"], "no-store, max-age=0")

    def test_subscription_route_requires_session_and_resolves_latest(self):
        self.assertEqual(self._get("/subscription").status_code, 401)
        cookie, _ = _session_cookie_header(self.conn, self.sample["customer_id"])
        ok = self._get("/subscription", cookie=cookie)
        self.assertEqual(ok.status_code, 200)
        self.assertIn("SUB-", ok.body)

    def test_method_not_allowed(self):
        req = portal_http.HttpRequest.build("POST", "/")
        self.assertEqual(self.app.handle(req).status_code, 405)

    def test_unknown_route_is_not_found_and_does_not_echo_path(self):
        res = self._get("/some/unknown/../path")
        self.assertEqual(res.status_code, 404)
        self.assertNotIn("unknown", res.body)

    def test_branded_route_uses_resolver_and_never_leaks_token(self):
        issued = portal_access.issue_token(
            self.conn, customer_id=self.sample["customer_id"], subscription_id=self.sample["subscription_id"]
        )
        res = self._get(f"/s/{issued.raw_token}")
        self.assertEqual(res.status_code, 200)
        self.assertNotIn(issued.raw_token, res.body)
        self.assertNotIn(issued.token_hash, res.body)
        line = self.app.access_line(
            portal_http.HttpRequest.build("GET", f"/s/{issued.raw_token}", remote_addr="203.0.113.5"),
            res,
        )
        self.assertNotIn(issued.raw_token, line)
        self.assertIn("/s/<redacted>", line)

        bad = self._get("/s/not-a-real-token")
        self.assertEqual(bad.status_code, 404)
        self.assertNotIn("not-a-real-token", bad.body)


class TestCookies(unittest.TestCase):
    def test_session_cookie_attributes(self):
        raw = portal_sessions.portal_tokens.generate_opaque_token()
        cookie = portal_cookies.build_session_set_cookie(raw, max_age=7200, same_site="Strict")
        self.assertIn("HttpOnly", cookie)
        self.assertIn("Secure", cookie)
        self.assertIn("SameSite=Strict", cookie)
        self.assertIn("Path=/", cookie)
        self.assertIn("Max-Age=7200", cookie)

    def test_parser_round_trip_and_no_leak_in_log(self):
        raw = portal_sessions.portal_tokens.generate_opaque_token()
        header = f"theme=dark; {portal_cookies.SESSION_COOKIE_NAME}={raw}; lang=my"
        parsed = portal_cookies.parse_cookie_header(header)
        self.assertEqual(parsed[portal_cookies.SESSION_COOKIE_NAME], raw)
        self.assertEqual(parsed["theme"], "dark")
        self.assertEqual(portal_cookies.session_id_from_cookie_header(header), raw)
        # The sanitizer must redact a Cookie header so the raw session never reaches a log.
        safe = access_log.sanitize_headers({"Cookie": header, "X-Real": "ok"})
        self.assertEqual(safe["Cookie"], "<redacted>")
        self.assertNotIn(raw, " ".join(safe.values()))

    def test_clear_cookie_expires(self):
        cookie = portal_cookies.build_clear_session_cookie()
        self.assertIn("Max-Age=0", cookie)
        self.assertIn("HttpOnly", cookie)


class TestCsrf(unittest.TestCase):
    def test_generate_verify_and_reject(self):
        key = portal_csrf.new_signing_key()
        now = datetime(2026, 6, 16, 6, 0, 0, tzinfo=tz.MMT)
        token = portal_csrf.issue_token(key, ttl_seconds=600, now=now)
        self.assertTrue(portal_csrf.verify_token(key, token, now=now).valid)
        # Tampered token rejected.
        self.assertFalse(portal_csrf.verify_token(key, token + "x", now=now).valid)
        self.assertEqual(portal_csrf.verify_token(key, "a.b", now=now).reason, "malformed")
        # Wrong key rejected.
        self.assertFalse(portal_csrf.verify_token(portal_csrf.new_signing_key(), token, now=now).valid)
        # Expired rejected (MMT clock honored).
        self.assertEqual(
            portal_csrf.verify_token(key, token, now=now + timedelta(seconds=601)).reason, "expired"
        )
        self.assertEqual(portal_csrf.verify_token(key, None, now=now).reason, "absent")

    def test_redaction_never_emits_raw(self):
        key = portal_csrf.new_signing_key()
        token = portal_csrf.issue_token(key)
        red = portal_csrf.redact(token)
        self.assertNotIn(token, red)
        self.assertIn("csrf:<redacted:", red)


class TestRateLimit(unittest.TestCase):
    def test_blocks_repeated_invalid_branded_attempts(self):
        limiter = rate_limit.RateLimiter(max_attempts=3, window_seconds=60, block_seconds=120)
        now = datetime(2026, 6, 16, 6, 0, 0, tzinfo=tz.MMT)
        key = rate_limit.safe_key("attacker-token", scope="branded")
        for _ in range(3):
            self.assertTrue(limiter.check(key, now=now).allowed)
        blocked = limiter.check(key, now=now)
        self.assertFalse(blocked.allowed)
        self.assertGreater(blocked.retry_after, 0)
        # Still blocked a minute later (block window refreshes).
        self.assertFalse(limiter.check(key, now=now + timedelta(seconds=60)).allowed)

    def test_window_rolls_over(self):
        limiter = rate_limit.RateLimiter(max_attempts=2, window_seconds=30, block_seconds=30)
        now = datetime(2026, 6, 16, 6, 0, 0, tzinfo=tz.MMT)
        key = rate_limit.safe_key("token-a")
        self.assertTrue(limiter.check(key, now=now).allowed)
        self.assertTrue(limiter.check(key, now=now).allowed)
        self.assertFalse(limiter.check(key, now=now).allowed)
        # After the window + block elapse, attempts are allowed again.
        later = now + timedelta(seconds=120)
        self.assertTrue(limiter.check(key, now=later).allowed)

    def test_safe_key_does_not_contain_raw_token(self):
        self.assertNotIn("attacker-token", rate_limit.safe_key("attacker-token"))


class TestRateLimitInHttp(unittest.TestCase):
    def test_repeated_branded_attempts_blocked_at_http_layer(self):
        conn = fresh_db(os.path.join(tempfile.mkdtemp(), "http_rl.sqlite3"))
        try:
            limiter = rate_limit.RateLimiter(max_attempts=2, window_seconds=60, block_seconds=120)
            app = portal_http.PortalHttpApp(conn, rate_limiter=limiter)
            statuses = []
            for _ in range(4):
                req = portal_http.HttpRequest.build("GET", "/s/repeated-bad-token")
                statuses.append(app.handle(req).status_code)
            self.assertEqual(statuses[:2], [404, 404])
            self.assertIn(429, statuses)
        finally:
            conn.close()


class TestAccessLogSanitizer(unittest.TestCase):
    def test_redacts_branded_token_path_and_query(self):
        self.assertEqual(access_log.sanitize_path("/s/abc123SECRETtoken"), "/s/<redacted>")
        self.assertEqual(access_log.sanitize_path("/plans?token=abc123SECRET&x=1"), "/plans")

    def test_redacts_secret_shaped_content(self):
        # Synthetic, non-real fixtures (kept short / assembled so the pre-commit scanner does not
        # treat them as concrete secrets) that still exercise every redaction branch.
        uuid_shape = "-".join(["1" * 8, "2" * 4, "3" * 4, "4" * 4, "5" * 12])
        proxy_shape = "vless://" + "mock-uri"
        text = f"/s/longtokenvalue uuid {uuid_shape} {proxy_shape} link"
        red = access_log.redact_text(text)
        self.assertNotIn("longtokenvalue", red)
        self.assertNotIn("vless://", red)
        self.assertIsNone(UUID_RE.search(red))

    def test_headers_drop_cookie_and_auth(self):
        safe = access_log.sanitize_headers({
            "Cookie": "unseen_portal_session=raw_secret_value",
            "Authorization": "Bearer raw_bearer_value",
            "Hiddify-API-Key": "secretkeyvalue",
            "Accept": "text/html",
        })
        self.assertEqual(safe["Cookie"], "<redacted>")
        self.assertEqual(safe["Authorization"], "<redacted>")
        self.assertEqual(safe["Hiddify-API-Key"], "<redacted>")
        self.assertEqual(safe["Accept"], "text/html")

    def test_format_event_redacts_ip_and_token(self):
        event = access_log.AccessEvent("GET", "/s/sometoken?token=x", 200, remote_addr="203.0.113.55")
        line = access_log.format_access_event(event)
        self.assertIn("/s/<redacted>", line)
        self.assertNotIn("sometoken", line)
        self.assertIn("ip:203.0.x.x", line)
        access_log.assert_safe(line, ("sometoken",))


class TestSidecarBoundary(unittest.TestCase):
    def setUp(self):
        self.conn = fresh_db(os.path.join(tempfile.mkdtemp(), "sidecar.sqlite3"))
        self.sample = _sample(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_valid_token_returns_placeholder_no_live_fetch(self):
        issued = portal_access.issue_token(
            self.conn, customer_id=self.sample["customer_id"], subscription_id=self.sample["subscription_id"]
        )
        result = sidecar_boundary.handle_branded(self.conn, issued.raw_token)
        self.assertEqual(result.status_code, 200)
        self.assertFalse(result.fetched_live)
        for needle in ("hiddify://", "vless://", "ss://", "hy2://", "/api/v2/"):
            self.assertNotIn(needle, result.body)
        line = sidecar_boundary.sanitized_access_line("198.51.100.7", result)
        self.assertNotIn(issued.raw_token, line)
        self.assertIn("/s/<redacted>", line)

    def test_invalid_and_expired_tokens(self):
        self.assertEqual(sidecar_boundary.handle_branded(self.conn, "nope").status_code, 404)
        now = datetime(2026, 6, 16, 6, 0, 0, tzinfo=tz.MMT)
        expired = portal_access.issue_token(
            self.conn, customer_id=self.sample["customer_id"],
            subscription_id=self.sample["subscription_id"], expires_at="2026-06-16 05:00:00", now=now,
        )
        self.assertEqual(sidecar_boundary.handle_branded(self.conn, expired.raw_token, now=now).status_code, 410)

    def test_no_network_during_sidecar(self):
        issued = portal_access.issue_token(
            self.conn, customer_id=self.sample["customer_id"], subscription_id=self.sample["subscription_id"]
        )
        original = socket.socket
        socket.socket = lambda *a, **k: (_ for _ in ()).throw(AssertionError("network attempted"))
        try:
            result = sidecar_boundary.handle_branded(self.conn, issued.raw_token)
            self.assertEqual(result.status_code, 200)
        finally:
            socket.socket = original


class TestLocalPreviewServerSafety(unittest.TestCase):
    def _run(self, args):
        return subprocess.run(
            ["python3", "bin/portal_local_preview_server.py", *args],
            cwd=REPO_ROOT, text=True, capture_output=True, timeout=30,
        )

    def test_does_not_autostart_without_flag(self):
        result = self._run([])
        self.assertEqual(result.returncode, 0)
        self.assertIn("NOT started", result.stdout)

    def test_refuses_public_bind(self):
        result = self._run(["--serve-local", "--host", "0.0.0.0"])
        self.assertEqual(result.returncode, 2)
        self.assertIn("REFUSED", result.stderr)

    def test_module_import_starts_nothing(self):
        # Importing the module must not instantiate an HTTPServer (i.e. must not bind a port).
        # We replace HTTPServer with a raising stub before import; a clean import proves no bind.
        code = (
            "import http.server, sys, os\n"
            "http.server.HTTPServer = lambda *a, **k: (_ for _ in ()).throw(AssertionError('bound'))\n"
            "sys.path.insert(0, os.getcwd())\n"
            "import bin.portal_local_preview_server as m\n"
            "assert hasattr(m, 'main')\n"
            "print('IMPORT_OK')\n"
        )
        result = subprocess.run(["python3", "-c", code], cwd=REPO_ROOT, text=True,
                                capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("IMPORT_OK", result.stdout)


class TestSmokeClisSanitized(unittest.TestCase):
    def test_http_and_sidecar_smoke_are_sanitized(self):
        for cmd in (["python3", "bin/portal_http_smoke.py"], ["python3", "bin/sidecar_boundary_smoke.py"]):
            with self.subTest(cmd=cmd):
                result = subprocess.run(cmd, cwd=REPO_ROOT, check=True, text=True,
                                        capture_output=True, timeout=60)
                self.assertIn("SMOKE_OK", result.stdout)
                self.assertNotIn("unseen_portal_session=", result.stdout)
                self.assertNotIn("vless://", result.stdout)
                self.assertIsNone(UUID_RE.search(result.stdout))


if __name__ == "__main__":
    unittest.main()

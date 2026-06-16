import json
import os
import tempfile
import unittest

from _helper import fresh_db
from backend import (
    account_service, bot_context, config, notification_service as notif,
    notification_sender, outbound_worker, runtime_gates, telegram_polling,
    telegram_transport,
)


class _MockOpener:
    """Captures the last request and returns a canned (status, body). Asserts no token leak path
    is needed here because the opener receives the URL but tests never log it."""
    def __init__(self, status=200, payload=None):
        self.calls = []
        self._status = status
        self._payload = payload if payload is not None else {"ok": True, "result": {}}

    def __call__(self, method, url, params, timeout):
        self.calls.append({"method": method, "url": url, "params": params, "timeout": timeout})
        return self._status, json.dumps(self._payload).encode()


class TestTransportDryRun(unittest.TestCase):
    def test_dry_run_records_no_network(self):
        t = telegram_transport.TelegramTransport()      # dry-run, no opener
        r = t.send_message(123, "hello")
        self.assertTrue(r.dry_run)
        self.assertTrue(r.ok)
        self.assertEqual(t.last_request().method, "sendMessage")
        self.assertEqual(t.last_request().params["chat_id"], 123)

    def test_token_redacted_everywhere(self):
        fake = "1234567890:" + ("A" * 35)
        t = telegram_transport.TelegramTransport(token=fake)
        self.assertNotIn(fake, repr(t))
        self.assertNotIn("AAAAA", repr(t))
        self.assertIn("<redacted>", t.token_fingerprint)
        # the token-bearing URL is never exposed via any public attr/repr
        self.assertNotIn("api.telegram.org/bot1234567890", repr(t))

    def test_sendmessage_construction_no_token_in_params(self):
        op = _MockOpener()
        fake = "1234567890:" + ("B" * 35)
        t = telegram_transport.TelegramTransport(token=fake, live=True, opener=op)
        r = t.send_message(555, "hi", parse_mode="HTML")
        self.assertTrue(r.ok)
        self.assertFalse(r.dry_run)
        call = op.calls[-1]
        self.assertEqual(call["method"], "sendMessage")
        self.assertEqual(call["params"]["chat_id"], 555)
        self.assertEqual(call["params"]["text"], "hi")
        # token must NOT appear in the params dict (only inside the URL the opener receives)
        self.assertNotIn(fake, json.dumps(call["params"]))

    def test_get_updates_offset_param(self):
        op = _MockOpener(payload={"ok": True, "result": []})
        t = telegram_transport.TelegramTransport(token="1:x", live=True, opener=op)
        t.get_updates(offset=42)
        self.assertEqual(op.calls[-1]["params"]["offset"], 42)
        self.assertEqual(op.calls[-1]["method"], "getUpdates")


class TestRuntimeGates(unittest.TestCase):
    def tearDown(self):
        os.environ.pop(config.ALLOW_LIVE_BOT_SENDS_ENV, None)
        os.environ.pop(config.ALLOW_LIVE_BOT_POLLING_ENV, None)

    def test_send_gate_fail_closed(self):
        self.assertFalse(runtime_gates.live_send_gate().allowed)                      # nothing set
        self.assertFalse(runtime_gates.live_send_gate(live_send=True, confirm=True).allowed)  # env missing
        os.environ[config.ALLOW_LIVE_BOT_SENDS_ENV] = "1"
        self.assertFalse(runtime_gates.live_send_gate(live_send=True).allowed)         # confirm missing
        self.assertFalse(runtime_gates.live_send_gate(confirm=True).allowed)           # flag missing
        self.assertTrue(runtime_gates.live_send_gate(live_send=True, confirm=True).allowed)

    def test_send_gate_strict_env_value(self):
        os.environ[config.ALLOW_LIVE_BOT_SENDS_ENV] = "true"   # not exactly "1"
        self.assertFalse(runtime_gates.live_send_gate(live_send=True, confirm=True).allowed)

    def test_poll_gate_fail_closed(self):
        self.assertFalse(runtime_gates.live_poll_gate(live_poll=True, confirm=True).allowed)
        os.environ[config.ALLOW_LIVE_BOT_POLLING_ENV] = "1"
        self.assertTrue(runtime_gates.live_poll_gate(live_poll=True, confirm=True).allowed)


class TestPollingRunner(unittest.TestCase):
    def setUp(self):
        self.conn = fresh_db(os.path.join(tempfile.mkdtemp(), "t.sqlite3"))
        self.ctx = bot_context.BotContext(admin_ids=frozenset())
        self.runner = telegram_polling.TelegramPollingRunner(self.conn, self.ctx)

    def tearDown(self):
        self.conn.close()
        os.environ.pop(config.ALLOW_LIVE_BOT_POLLING_ENV, None)

    def test_routes_start_and_tracks_offset(self):
        updates = [
            {"update_id": 10, "message": {"from": {"id": 900}, "chat": {"id": 900}, "text": "/start"}},
            {"update_id": 11, "message": {"from": {"id": 900}, "chat": {"id": 900}, "text": "/plans"}},
        ]
        s = self.runner.poll_batch(updates)
        self.assertEqual(s.processed, 2)
        self.assertEqual(s.handled[0], "/start")
        self.assertEqual(s.next_offset, 12)   # last update_id + 1
        # /start created exactly one customer + telegram platform account
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0], 1)

    def test_invalid_update_in_batch_does_not_crash(self):
        s = self.runner.poll_batch([{"weird": True}, 42, {"update_id": 5, "message": {}}])
        self.assertEqual(s.processed, 3)
        self.assertTrue(all(h == "invalid" for h in s.handled))

    def test_live_poll_refused_without_gate(self):
        with self.assertRaises(telegram_polling.LivePollingRefusedError):
            self.runner.run_live_once(live_poll=True, confirm=True)   # env not set
        with self.assertRaises(telegram_polling.LivePollingRefusedError):
            self.runner.run_live_once(live_poll=False, confirm=False)


class TestNotificationSender(unittest.TestCase):
    def setUp(self):
        self.conn = fresh_db(os.path.join(tempfile.mkdtemp(), "t.sqlite3"))
        self.cid = account_service.resolve_customer(self.conn, "telegram", "900100")  # numeric tg id

    def tearDown(self):
        self.conn.close()
        os.environ.pop(config.ALLOW_LIVE_BOT_SENDS_ENV, None)

    def _enqueue(self, payload_ref="bot:welcome:x"):
        return notif.enqueue_notification(self.conn, self.cid, "telegram", "transactional", payload_ref)

    def test_mock_success_marks_sent(self):
        mid = self._enqueue()
        summary = outbound_worker.run_once(self.conn)   # dry-run transport, default "ok"
        self.assertEqual(summary.sent, 1)
        self.assertEqual(notif.get_message(self.conn, mid)["status"], "sent")

    def test_retryable_failure_keeps_queued_and_increments(self):
        mid = self._enqueue()
        summary = outbound_worker.run_once(self.conn, simulate=lambda row: "retry")
        self.assertEqual(summary.requeued, 1)
        row = notif.get_message(self.conn, mid)
        self.assertEqual(row["status"], "queued")
        self.assertEqual(row["attempts"], 1)
        self.assertIsNotNone(row["next_attempt_at"])

    def test_permanent_failure_marks_dead(self):
        mid = self._enqueue()
        outbound_worker.run_once(self.conn, simulate=lambda row: "permanent")
        self.assertEqual(notif.get_message(self.conn, mid)["status"], "dead")

    def test_max_attempts_dead_letters(self):
        mid = self._enqueue()
        # default max_attempts is 5 → 5 retryable failures dead-letters it
        for _ in range(5):
            outbound_worker.run_once(self.conn, simulate=lambda row: "retry")
            # requeue keeps it 'queued' until the 5th, which flips to 'dead'
            if notif.get_message(self.conn, mid)["status"] == "dead":
                break
        self.assertEqual(notif.get_message(self.conn, mid)["status"], "dead")
        self.assertEqual(notif.get_message(self.conn, mid)["attempts"], 5)

    def test_payload_ref_only_no_raw_body(self):
        mid = self._enqueue("delivery:sub:42")
        row = notif.get_message(self.conn, mid)
        self.assertEqual(row["payload_ref"], "delivery:sub:42")
        for needle in ("http", "://", "vless", "ss:", "hy2", "BEGIN"):
            self.assertNotIn(needle, str(row["payload_ref"]))

    def test_live_send_refused_without_gate(self):
        self._enqueue()
        with self.assertRaises(notification_sender.LiveSendRefusedError):
            outbound_worker.run_once(self.conn, live_send=True, confirm=True)  # env not set

    def test_live_uses_mock_transport_even_when_gated(self):
        # Even with the env gate + flags, the test injects a MOCK transport — no real network.
        os.environ[config.ALLOW_LIVE_BOT_SENDS_ENV] = "1"
        op = _MockOpener()
        t = telegram_transport.TelegramTransport(token="1:y", live=True, opener=op)
        mid = self._enqueue()
        summary = outbound_worker.run_once(self.conn, transport=t, live_send=True, confirm=True)
        self.assertTrue(summary.live)
        self.assertEqual(summary.sent, 1)
        self.assertEqual(op.calls[-1]["method"], "sendMessage")
        self.assertEqual(notif.get_message(self.conn, mid)["status"], "sent")


class TestNoNetworkAndNoHiddify(unittest.TestCase):
    def test_full_dry_run_makes_no_network_call(self):
        import urllib.request
        conn = fresh_db(os.path.join(tempfile.mkdtemp(), "t.sqlite3"))
        cid = account_service.resolve_customer(conn, "telegram", "900200")
        notif.enqueue_notification(conn, cid, "telegram", "transactional", "bot:welcome:1")
        ctx = bot_context.BotContext(admin_ids=frozenset())
        runner = telegram_polling.TelegramPollingRunner(conn, ctx)
        orig = urllib.request.urlopen
        urllib.request.urlopen = lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("network call attempted in dry-run transport!"))
        try:
            runner.poll_batch([{"update_id": 1, "message": {"from": {"id": 900200},
                                "chat": {"id": 900200}, "text": "/start"}}])
            outbound_worker.run_once(conn)
        finally:
            urllib.request.urlopen = orig
        conn.close()


if __name__ == "__main__":
    unittest.main()

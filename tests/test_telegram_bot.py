import os
import tempfile
import unittest

from _helper import fresh_db
from backend import (
    bot_context, config, notification_service as notif,
    telegram_adapter, telegram_commands as tc, telegram_messages as msg,
    telegram_router,
)


def _msg(uid, text):
    return {"message": {"from": {"id": uid}, "chat": {"id": uid}, "text": text}}


class TestAdapter(unittest.TestCase):
    def test_dry_run_send_records_no_network(self):
        a = telegram_adapter.TelegramAdapter()
        res = a.send_message(123, "hello")
        self.assertTrue(res["dry_run"])
        self.assertEqual(len(a.outbox), 1)
        self.assertEqual(a.last_text(), "hello")

    def test_live_send_refused(self):
        a = telegram_adapter.TelegramAdapter(live=True)
        with self.assertRaises(telegram_adapter.LiveSendDisabledError):
            a.send_message(1, "x")
        self.assertTrue(config.PHASE5_LIVE_SEND_DISABLED)

    def test_token_redaction(self):
        # Build a token-shaped value at runtime so no token-shaped literal sits in source.
        fake = "1234567890:" + ("A" * 35)
        a = telegram_adapter.TelegramAdapter(token=fake)
        self.assertNotIn(fake, repr(a))
        self.assertNotIn("AAAAA", repr(a))
        self.assertIn("<redacted>", a.token_fingerprint)
        self.assertEqual(telegram_adapter.redact_token(None), "tg:<absent>")


class TestBotContext(unittest.TestCase):
    def tearDown(self):
        for k in (config.ADMIN_TELEGRAM_IDS_ENV, config.ADMIN_TELEGRAM_IDS_ENV_FALLBACK,
                  config.TELEGRAM_BOT_TOKEN_ENV):
            os.environ.pop(k, None)

    def test_admin_ids_parsed_from_env_no_hardcode(self):
        os.environ[config.ADMIN_TELEGRAM_IDS_ENV] = "111, 222 ,bad,, 333"
        ctx = bot_context.BotContext.from_env()
        self.assertEqual(ctx.admin_ids, frozenset({111, 222, 333}))  # bad/blank ignored
        self.assertTrue(ctx.is_admin(222))
        self.assertFalse(ctx.is_admin(999))
        self.assertEqual(ctx.admin_count, 3)

    def test_fallback_env_name(self):
        os.environ[config.ADMIN_TELEGRAM_IDS_ENV_FALLBACK] = "777"
        ctx = bot_context.BotContext.from_env()
        self.assertTrue(ctx.is_admin(777))

    def test_placeholder_is_not_admin(self):
        os.environ[config.ADMIN_TELEGRAM_IDS_ENV] = "__PLACEHOLDER__"
        ctx = bot_context.BotContext.from_env()
        self.assertEqual(ctx.admin_count, 0)

    def test_no_admin_env_means_empty(self):
        ctx = bot_context.BotContext.from_env()
        self.assertEqual(ctx.admin_count, 0)
        self.assertFalse(ctx.is_admin(1))


class TestRouter(unittest.TestCase):
    def setUp(self):
        self.conn = fresh_db(os.path.join(tempfile.mkdtemp(), "t.sqlite3"))
        self.ctx = bot_context.BotContext(admin_ids=frozenset({42}))
        self.adapter = telegram_adapter.TelegramAdapter()
        self.router = telegram_router.TelegramRouter(self.conn, self.ctx, self.adapter)

    def tearDown(self):
        self.conn.close()

    def test_start_creates_customer_and_platform_account(self):
        r = self.router.handle_update(_msg(1001, "/start"))
        self.assertEqual(r.handled, "/start")
        self.assertIsNotNone(r.customer_id)
        pa = self.conn.execute(
            "SELECT customer_id FROM platform_accounts WHERE platform_name='telegram' AND platform_user_id='1001'"
        ).fetchone()
        self.assertEqual(int(pa[0]), r.customer_id)
        # telegram id stored as platform account, not as the customer identity
        self.assertNotEqual(str(r.customer_id), "1001")

    def test_start_idempotent(self):
        a = self.router.handle_update(_msg(1001, "/start")).customer_id
        b = self.router.handle_update(_msg(1001, "/start")).customer_id
        self.assertEqual(a, b)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0], 1)

    def test_invalid_update_does_not_crash(self):
        for bad in (None, {}, {"message": {}}, {"message": {"from": {}}}, 42, "x", {"callback_query": {}}):
            r = self.router.handle_update(bad)
            self.assertEqual(r.handled, "invalid")
            self.assertEqual(r.reply_text, msg.INVALID_UPDATE)

    def test_unknown_command_fallback(self):
        r = self.router.handle_update(_msg(1001, "blah blah"))
        self.assertEqual(r.handled, "unknown")
        self.assertEqual(r.reply_text, msg.UNKNOWN)

    def test_plans_render_from_db_not_hardcoded(self):
        r = self.router.handle_update(_msg(1001, "/plans"))
        # remove a plan from DB → it must disappear from the rendered view (proves DB-driven)
        self.assertIn("TRIAL", r.reply_text)
        self.conn.execute("DELETE FROM plans WHERE plan_code='TRIAL'")
        self.conn.commit()
        r2 = self.router.handle_update(_msg(1001, "/plans"))
        self.assertNotIn("TRIAL", r2.reply_text)
        self.assertIn("BASIC_1M", r2.reply_text)

    def test_sg_only_for_pro_max(self):
        r = self.router.handle_update(_msg(1001, "/plans"))
        text = r.reply_text
        # SG must be entitled for PRO/MAX and not for BASIC/CORE
        self.assertIn("SG", text)  # appears via PRO/MAX rows
        for line in text.splitlines():
            if line.strip().startswith("• Basic") or line.strip().startswith("• Core"):
                self.assertNotIn("SG", line)

    def test_fast_label_rule_in_render(self):
        text = self.router.handle_update(_msg(1001, "/plans")).reply_text
        lines = text.splitlines()
        # find the Basic block (one fast tier -> "Fast") and Plus block (two -> Fast1/Fast2)
        joined = "\n".join(lines)
        self.assertIn("Fast/Secure", joined)            # single fast tier
        self.assertIn("Fast1/Fast2/Secure", joined)     # both fast tiers

    def test_admin_route_env_driven(self):
        # admin id 42 (from ctx) sees the summary; a non-admin sees denial
        radm = self.router.handle_update(_msg(42, "/admin"))
        self.assertTrue(radm.is_admin)
        self.assertIn("Admin", radm.reply_text)
        rno = self.router.handle_update(_msg(43, "/admin"))
        self.assertFalse(rno.is_admin)
        self.assertEqual(rno.reply_text, msg.ADMIN_DENIED)

    def test_welcome_help_menu_burmese_present(self):
        # Burmese (Myanmar script) code points must be present in the core copy
        def has_burmese(s):
            return any("က" <= ch <= "႟" for ch in s)
        self.assertTrue(has_burmese(msg.WELCOME))
        self.assertTrue(has_burmese(msg.MAIN_MENU))
        self.assertTrue(has_burmese(msg.help_text()))
        # English product terms kept verbatim
        self.assertIn("Plan", msg.MAIN_MENU)

    def test_notification_enqueue_payload_ref_only(self):
        # the bot may enqueue an internal notification; it stores a payload_ref, not a body/secret
        self.router.handle_update(_msg(1001, "/start"))
        cid = self.conn.execute(
            "SELECT customer_id FROM platform_accounts WHERE platform_user_id='1001'").fetchone()[0]
        mid = notif.enqueue_notification(self.conn, cid, "telegram", "transactional", "bot:welcome:1001")
        row = notif.get_message(self.conn, mid)
        self.assertEqual(row["status"], "queued")
        self.assertEqual(row["payload_ref"], "bot:welcome:1001")
        for needle in ("http", "://", "vless", "ss:", "hy2"):
            self.assertNotIn(needle, row["payload_ref"])

    def test_no_secret_in_rendered_text(self):
        for text in (msg.WELCOME, msg.MAIN_MENU, msg.help_text(), msg.LINK_PROMPT,
                     self.router.handle_update(_msg(1001, "/plans")).reply_text):
            for needle in ("Hiddify-API-Key", "vless://", "ss://", "hy2://", "BEGIN", "token=", "uuid="):
                self.assertNotIn(needle, text)


class TestNoNetwork(unittest.TestCase):
    def test_router_flow_makes_no_network_call(self):
        import urllib.request
        conn = fresh_db(os.path.join(tempfile.mkdtemp(), "t.sqlite3"))
        ctx = bot_context.BotContext(admin_ids=frozenset())
        router = telegram_router.TelegramRouter(conn, ctx, telegram_adapter.TelegramAdapter())
        orig = urllib.request.urlopen
        urllib.request.urlopen = lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("network call attempted in dry-run bot!"))
        try:
            for text in ("/start", "/plans", "/account", "/help", "/link", "/admin", "x"):
                router.handle_update(_msg(2002, text))
        finally:
            urllib.request.urlopen = orig
        conn.close()


if __name__ == "__main__":
    unittest.main()

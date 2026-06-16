import os
import tempfile
import unittest

from _helper import fresh_db
from backend import account_service as acct, notification_service as notif


class TestNotificationService(unittest.TestCase):
    def setUp(self):
        self.conn = fresh_db(os.path.join(tempfile.mkdtemp(), "t.sqlite3"))
        self.cid = acct.resolve_customer(self.conn, "telegram", "n-1")

    def tearDown(self):
        self.conn.close()

    def test_enqueue_defaults_to_queued(self):
        mid = notif.enqueue_notification(self.conn, self.cid, "telegram", "transactional", "tmpl:welcome")
        row = notif.get_message(self.conn, mid)
        self.assertEqual(row["status"], "queued")
        self.assertEqual(row["attempts"], 0)
        self.assertEqual(row["payload_ref"], "tmpl:welcome")
        # the queue stores a reference, NOT a raw body
        self.assertNotIn("http", str(row["payload_ref"]))

    def test_invalid_channel_and_purpose_rejected(self):
        with self.assertRaises(notif.InvalidChannelError):
            notif.enqueue_notification(self.conn, self.cid, "sms", "transactional", "x")
        with self.assertRaises(notif.InvalidPurposeError):
            notif.enqueue_notification(self.conn, self.cid, "telegram", "spam", "x")

    def test_mark_sent_transition(self):
        mid = notif.enqueue_notification(self.conn, self.cid, "telegram", "reminder", "tmpl:expiry")
        notif.mark_sent(self.conn, mid)
        row = notif.get_message(self.conn, mid)
        self.assertEqual(row["status"], "sent")
        self.assertIsNotNone(row["sent_at"])

    def test_retry_then_dead_letter(self):
        mid = notif.enqueue_notification(self.conn, self.cid, "messenger", "transactional", "tmpl:x")
        # max_attempts default is 5 -> first 4 failures keep it queued, the 5th dead-letters
        for i in range(4):
            status = notif.mark_failed_or_retry(self.conn, mid, error_ref="ref:timeout")
            self.assertEqual(status, "queued", f"attempt {i+1}")
        status = notif.mark_failed_or_retry(self.conn, mid, error_ref="ref:timeout")
        self.assertEqual(status, "dead")
        row = notif.get_message(self.conn, mid)
        self.assertEqual(row["status"], "dead")
        self.assertEqual(row["attempts"], 5)
        self.assertEqual(row["last_error"], "ref:timeout")  # sanitized ref, not a secret
        self.assertIsNone(row["next_attempt_at"])

    def test_mark_dead_directly(self):
        mid = notif.enqueue_notification(self.conn, self.cid, "viber", "promo", "tmpl:promo")
        notif.mark_dead(self.conn, mid, reason_ref="ref:blocked")
        self.assertEqual(notif.get_message(self.conn, mid)["status"], "dead")

    def test_policy_placeholder_behavior(self):
        # Telegram may send all purposes
        self.assertEqual(notif.classify_policy("telegram", "promo").action, "send")
        self.assertEqual(notif.classify_policy("telegram", "transactional").action, "send")
        # Messenger out-of-window: transactional sends, reminder needs a template, promo suppressed
        self.assertEqual(notif.classify_policy("messenger", "transactional", within_session=False).action, "send")
        self.assertEqual(notif.classify_policy("messenger", "reminder", within_session=False).action, "template_required")
        self.assertEqual(notif.classify_policy("messenger", "promo", within_session=False).action, "suppress")
        self.assertEqual(notif.classify_policy("whatsapp", "promo", within_session=False).action, "suppress")
        # Viber out-of-session non-transactional queues
        self.assertEqual(notif.classify_policy("viber", "reminder", within_session=False).action, "queue")
        # in-session always sends
        self.assertEqual(notif.classify_policy("messenger", "promo", within_session=True).action, "send")

    def test_queue_counts(self):
        a = notif.enqueue_notification(self.conn, self.cid, "telegram", "transactional", "r1")
        notif.enqueue_notification(self.conn, self.cid, "telegram", "reminder", "r2")
        notif.mark_sent(self.conn, a)
        counts = notif.queue_counts(self.conn)
        self.assertEqual(counts.get("sent"), 1)
        self.assertEqual(counts.get("queued"), 1)


if __name__ == "__main__":
    unittest.main()

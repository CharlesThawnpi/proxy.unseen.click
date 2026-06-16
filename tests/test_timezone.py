import unittest
import subprocess
from datetime import datetime, timezone, timedelta

from _helper import REPO_ROOT  # noqa: F401
from backend import timezone as tz


class TestMyanmarTimePolicy(unittest.TestCase):
    def test_myanmar_time_offset(self):
        sample = datetime(2026, 6, 16, 12, 0, tzinfo=timezone.utc)
        converted = tz.to_mmt(sample)
        self.assertEqual(converted.utcoffset(), timedelta(hours=6, minutes=30))
        self.assertEqual(tz.MMT_TZ_NAME, "Asia/Yangon")
        self.assertEqual(tz.MMT_ABBR, "MMT")

    def test_now_mmt_is_timezone_aware(self):
        now = tz.now_mmt()
        self.assertIsNotNone(now.tzinfo)
        self.assertEqual(now.utcoffset(), timedelta(hours=6, minutes=30))

    def test_utc_input_converts_to_mmt(self):
        utc_dt = datetime(2026, 1, 1, 18, 0, tzinfo=timezone.utc)
        converted = tz.to_mmt(utc_dt)
        self.assertEqual(converted.year, 2026)
        self.assertEqual(converted.month, 1)
        self.assertEqual(converted.day, 2)
        self.assertEqual(converted.hour, 0)
        self.assertEqual(converted.minute, 30)

    def test_format_labels_mmt(self):
        utc_dt = datetime(2026, 6, 16, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(tz.format_mmt(utc_dt), "2026-06-16 06:30:00 MMT")
        self.assertIn("Asia/Yangon", tz.format_mmt(utc_dt, include_tz_name=True))

    def test_subscription_style_start_end_examples_use_mmt(self):
        start = tz.parse_mmt("2026-06-16 09:00:00")
        end = start + timedelta(days=30)
        self.assertEqual(tz.format_mmt(start), "2026-06-16 09:00:00 MMT")
        self.assertEqual(tz.format_mmt(end), "2026-07-16 09:00:00 MMT")
        self.assertEqual(tz.storage_mmt(end), "2026-07-16T09:00:00+06:30")

    def test_naive_external_datetime_rejected(self):
        with self.assertRaises(ValueError):
            tz.to_mmt(datetime(2026, 6, 16, 9, 0))

    def test_timezone_audit_cli_sanitized_summary(self):
        result = subprocess.run(
            ["python3", "bin/timezone_audit.py", "backend", "docs/TIMEZONE_POLICY.md"],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        self.assertIn("timestamp_audit", result.stdout)
        self.assertIn("files_with_hits=", result.stdout)
        self.assertNotIn("://", result.stdout)


if __name__ == "__main__":
    unittest.main()

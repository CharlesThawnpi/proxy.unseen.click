import os
import socket
import tempfile
import unittest

from _helper import fresh_db
from backend import (
    alerting, availability, health_monitor, metric_writer, node_probe, node_resilience as nr,
    probe_sanitizer, telegram_messages as msg,
)


def _pr(node_code, **kw):
    return node_probe.ProbeResult(node_code=node_code, **kw)


def _add_node(conn, code, region, status):
    conn.execute("INSERT OR IGNORE INTO proxy_nodes(node_code,region_code,status) VALUES (?,?,?)",
                 (code, region, status))
    conn.commit()


class TestProbeSanitizer(unittest.TestCase):
    def test_sanitize_error_codes(self):
        self.assertEqual(probe_sanitizer.sanitize_error(socket.timeout()), probe_sanitizer.PROBE_TIMEOUT)
        self.assertEqual(probe_sanitizer.sanitize_error(TimeoutError()), probe_sanitizer.PROBE_TIMEOUT)
        # an error whose message carries a host/URL must NOT surface that — only a code
        err = OSError("connect to https://node-de.unseen.click/SECRET/api/v2 failed 1.2.3.4")
        code = probe_sanitizer.sanitize_error(err)
        self.assertEqual(code, probe_sanitizer.PROBE_ERROR_SANITIZED)
        self.assertNotIn("unseen.click", code)
        self.assertNotIn("1.2.3.4", code)

    def test_probe_result_sanitized_has_no_secret_fields(self):
        pr = _pr("de1", status="down", reasons=[alerting.TCP_443_DOWN])
        d = pr.sanitized()
        blob = str(d)
        # secret-shaped VALUES must never appear (field names like panel_http_status are fine)
        for needle in ("vless://", "ss://", "hy2://", "hiddify://", "Hiddify-API-Key",
                       "BEGIN", "5.249.160.59", "/api/v2/admin"):
            self.assertNotIn(needle, blob)
        # only declared safe keys present
        self.assertEqual(set(d) >= {"node_code", "status", "reasons", "tcp_443_ok"}, True)


class TestMetricWriter(unittest.TestCase):
    def setUp(self):
        self.conn = fresh_db(os.path.join(tempfile.mkdtemp(), "t.sqlite3"))

    def tearDown(self):
        self.conn.close()

    def test_appends_rows(self):
        before = self.conn.execute("SELECT COUNT(*) FROM node_metrics").fetchone()[0]
        metric_writer.write_metric(self.conn, _pr("de1", cpu_pct=10, ram_pct=20, disk_pct=30))
        metric_writer.write_metric(self.conn, _pr("de1", cpu_pct=11, ram_pct=21, disk_pct=31))
        after = self.conn.execute("SELECT COUNT(*) FROM node_metrics").fetchone()[0]
        self.assertEqual(after - before, 2)            # append-only
        row = self.conn.execute("SELECT cpu_pct FROM node_metrics ORDER BY id DESC LIMIT 1").fetchone()
        self.assertEqual(row[0], 11)


class TestAlertEvaluator(unittest.TestCase):
    def setUp(self):
        self.conn = fresh_db(os.path.join(tempfile.mkdtemp(), "t.sqlite3"))

    def tearDown(self):
        self.conn.close()

    def _open(self, node="de1"):
        return {(r["metric"], r["level"]) for r in self.conn.execute(
            "SELECT metric, level FROM node_alerts WHERE node_code=? AND cleared_at IS NULL", (node,))}

    def test_warn_at_75(self):
        alerting.evaluate(self.conn, _pr("de1", tcp_443_ok=True, cpu_pct=75))
        self.assertIn(("cpu", "WARN"), self._open())

    def test_critical_at_90(self):
        alerting.evaluate(self.conn, _pr("de1", tcp_443_ok=True, ram_pct=90))
        self.assertIn(("ram", "CRITICAL"), self._open())

    def test_down_for_tcp443_and_panel(self):
        alerting.evaluate(self.conn, _pr("de1", tcp_443_ok=False, panel_http_status=503))
        opens = self._open()
        self.assertIn(("tcp_443", "DOWN"), opens)
        self.assertIn(("panel", "DOWN"), opens)

    def test_no_duplicate_open_alerts(self):
        alerting.evaluate(self.conn, _pr("de1", tcp_443_ok=True, cpu_pct=92))
        alerting.evaluate(self.conn, _pr("de1", tcp_443_ok=True, cpu_pct=93))   # still CRITICAL cpu
        n = self.conn.execute(
            "SELECT COUNT(*) FROM node_alerts WHERE node_code='de1' AND metric='cpu' AND cleared_at IS NULL"
        ).fetchone()[0]
        self.assertEqual(n, 1)

    def test_level_change_clears_old_raises_new(self):
        alerting.evaluate(self.conn, _pr("de1", tcp_443_ok=True, cpu_pct=80))   # WARN
        alerting.evaluate(self.conn, _pr("de1", tcp_443_ok=True, cpu_pct=95))   # CRITICAL
        self.assertIn(("cpu", "CRITICAL"), self._open())
        self.assertNotIn(("cpu", "WARN"), self._open())
        # old WARN row is cleared (not deleted)
        cleared = self.conn.execute(
            "SELECT COUNT(*) FROM node_alerts WHERE metric='cpu' AND level='WARN' AND cleared_at IS NOT NULL"
        ).fetchone()[0]
        self.assertEqual(cleared, 1)

    def test_resolved_condition_clears_alert(self):
        alerting.evaluate(self.conn, _pr("de1", tcp_443_ok=True, cpu_pct=92))   # open CRITICAL
        alerting.evaluate(self.conn, _pr("de1", tcp_443_ok=True, cpu_pct=10))   # resolved
        self.assertNotIn(("cpu", "CRITICAL"), self._open())
        self.assertEqual(self._open(), set())

    def test_thresholds_from_settings(self):
        self.conn.execute("UPDATE settings SET value='50' WHERE key='node_alert_warn_pct'")
        self.conn.commit()
        self.assertEqual(alerting.thresholds(self.conn)[0], 50)
        alerting.evaluate(self.conn, _pr("de1", tcp_443_ok=True, cpu_pct=55))   # now WARN at 55
        self.assertIn(("cpu", "WARN"), self._open())


class TestResilienceIntegration(unittest.TestCase):
    def setUp(self):
        self.conn = fresh_db(os.path.join(tempfile.mkdtemp(), "t.sqlite3"))

    def tearDown(self):
        self.conn.close()

    def test_down_alert_makes_node_down_and_dropped(self):
        _add_node(self.conn, "us1", "us", "live")
        alerting.evaluate(self.conn, _pr("us1", tcp_443_ok=False))   # DOWN
        self.assertEqual(nr.node_health(self.conn, "us1"), nr.HEALTH_DOWN)
        r = nr.node_readiness(self.conn, "us1", "us", "live")
        self.assertFalse(r.dry_run_candidate)            # down → dropped
        self.assertFalse(r.live_ready)
        self.assertIn(nr.NODE_DOWN, r.reasons)
        av = availability.resolve(self.conn, "CORE_1M", mode=availability.MODE_LIVE)
        self.assertNotIn("us", av.available_regions)

    def test_critical_resource_degrades_not_down(self):
        _add_node(self.conn, "us1", "us", "live")
        alerting.evaluate(self.conn, _pr("us1", tcp_443_ok=True, cpu_pct=95))  # CRITICAL resource
        self.assertEqual(nr.node_health(self.conn, "us1"), nr.HEALTH_DEGRADED)
        r = nr.node_readiness(self.conn, "us1", "us", "live")
        self.assertTrue(r.dry_run_candidate)             # degraded still a dry-run candidate (policy)
        self.assertFalse(r.live_ready)                   # but NOT live-ready
        self.assertIn(nr.NODE_DEGRADED, r.reasons)

    def test_warn_resource_degrades(self):
        _add_node(self.conn, "us1", "us", "live")
        alerting.evaluate(self.conn, _pr("us1", tcp_443_ok=True, disk_pct=80))  # WARN
        self.assertEqual(nr.node_health(self.conn, "us1"), nr.HEALTH_DEGRADED)

    def test_de1_still_blocks_live(self):
        r = nr.node_readiness(self.conn, "de1", "de", "test")
        self.assertFalse(r.live_ready)
        self.assertIn(nr.NODE_STATUS_TEST, r.reasons)
        # Phase 9: leaked-key blocker cleared; de1 still blocks live via status=test +
        # the remaining real-device protocol connect PASS requirement.
        self.assertIn(nr.REALDEVICE_PROTOCOL_TEST_PENDING, r.reasons)
        self.assertNotIn(nr.LEAKED_KEY_REBUILD_PENDING, r.reasons)


class TestMonitorOnce(unittest.TestCase):
    def setUp(self):
        self.conn = fresh_db(os.path.join(tempfile.mkdtemp(), "t.sqlite3"))

    def tearDown(self):
        self.conn.close()

    def test_dry_run_writes_nothing(self):
        before_m = self.conn.execute("SELECT COUNT(*) FROM node_metrics").fetchone()[0]
        before_a = self.conn.execute("SELECT COUNT(*) FROM node_alerts").fetchone()[0]
        s = health_monitor.monitor_once(self.conn, write=False)
        self.assertFalse(s.write)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM node_metrics").fetchone()[0], before_m)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM node_alerts").fetchone()[0], before_a)

    def test_write_mode_writes_metrics_and_alerts(self):
        prober = node_probe.MockProber({"de1": {"status": "degraded", "tcp_443_ok": True,
                                                 "cpu_pct": 95}})
        s = health_monitor.monitor_once(self.conn, prober=prober, write=True)
        self.assertTrue(s.write)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM node_metrics").fetchone()[0], 1)
        self.assertIn(("cpu", "CRITICAL"), {(r["metric"], r["level"]) for r in self.conn.execute(
            "SELECT metric, level FROM node_alerts WHERE cleared_at IS NULL")})

    def test_monitor_idempotent_no_dup_alerts(self):
        prober = node_probe.MockProber({"de1": {"status": "degraded", "tcp_443_ok": True, "cpu_pct": 95}})
        health_monitor.monitor_once(self.conn, prober=prober, write=True)
        health_monitor.monitor_once(self.conn, prober=prober, write=True)
        n = self.conn.execute(
            "SELECT COUNT(*) FROM node_alerts WHERE metric='cpu' AND cleared_at IS NULL").fetchone()[0]
        self.assertEqual(n, 1)

    def test_no_network_in_dry_run_monitor(self):
        import urllib.request
        orig = urllib.request.urlopen
        urllib.request.urlopen = lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("network attempted in mock monitor!"))
        try:
            health_monitor.monitor_once(self.conn, write=True)   # mock prober → no network
        finally:
            urllib.request.urlopen = orig


class TestCustomerMessageSafety(unittest.TestCase):
    def test_no_secrets_or_ip_in_availability_copy(self):
        for s in (msg.region_unavailable("de"), msg.region_test_only("de"),
                  msg.protocol_unavailable("de", "Fast1")):
            for needle in ("5.249.160.59", "node-de.unseen.click", "vless://", "ss://", "hy2://",
                           "uuid", "/api/v2/", "token", "Hiddify-API-Key"):
                self.assertNotIn(needle, s)


if __name__ == "__main__":
    unittest.main()

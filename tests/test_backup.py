import os
import tempfile
import unittest

from _helper import fresh_db
from backend import account_service as acct, backup


class TestBackup(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = os.path.join(self.tmp, "src.sqlite3")
        conn = fresh_db(self.db)
        # add some real rows so the snapshot has content + FK relationships to verify
        acct.resolve_customer(conn, "telegram", "b-1")
        conn.close()
        self.out = os.path.join(self.tmp, "backups")

    def test_dry_run_writes_nothing(self):
        res = backup.online_backup(self.db, self.out, dry_run=True)
        self.assertTrue(res.ok)
        self.assertTrue(res.dry_run)
        self.assertIsNone(res.backup_path)
        self.assertFalse(os.path.exists(self.out))  # nothing created

    def test_online_backup_uses_sqlite_backup_and_verifies(self):
        res = backup.online_backup(self.db, self.out)
        self.assertTrue(res.ok)
        self.assertFalse(res.dry_run)
        self.assertTrue(os.path.exists(res.backup_path))
        self.assertEqual(res.integrity, "ok")
        self.assertEqual(res.fk_violations, 0)
        # the restored snapshot independently passes integrity + FK checks
        integrity, fk = backup.verify_backup(res.backup_path)
        self.assertEqual(integrity, "ok")
        self.assertEqual(fk, 0)
        # data actually came across
        import sqlite3
        c = sqlite3.connect(res.backup_path)
        self.assertEqual(c.execute("SELECT COUNT(*) FROM customers").fetchone()[0], 1)
        c.close()

    def test_no_raw_wal_copy(self):
        # Sanity: the WAL/SHM sidecars of the SOURCE are never copied into the backup dir.
        backup.online_backup(self.db, self.out)
        names = os.listdir(self.out)
        self.assertFalse(any(n.endswith("-wal") or n.endswith("-shm") for n in names), names)

    def test_manifest_has_paths_not_secrets(self):
        env_path = "/opt/unseen-proxy/.env"  # a PATH, not contents
        res = backup.online_backup(self.db, self.out, include_env_path=env_path)
        self.assertEqual(res.env_path, env_path)
        with open(res.manifest_path, encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("sqlite3.Connection.backup()", text)
        self.assertIn(env_path, text)             # path recorded
        self.assertIn('"env_contents_backed_up": false', text)  # contents NOT read
        # no obvious secret-shaped assignment in the manifest
        for needle in ("API_KEY", "PRIVATE KEY", "password", "Hiddify-API-Key"):
            self.assertNotIn(needle, text)


if __name__ == "__main__":
    unittest.main()

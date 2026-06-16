import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def fresh_db(tmp_path: str):
    """Migrate + seed a temp DB; return an open connection."""
    from backend import migrate, seed, db as dbmod
    migrate.migrate_path(tmp_path)
    conn = dbmod.connect(tmp_path)
    seed.seed(conn)
    return conn

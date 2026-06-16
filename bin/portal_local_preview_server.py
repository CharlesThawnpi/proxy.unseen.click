#!/usr/bin/env python3
"""Local-only, loopback-only preview server for the portal HTTP adapter.

SAFETY CONTRACT (Phase 8C):
  * Importing this module starts NOTHING.
  * Running it without --serve-local starts NOTHING; it prints guidance and exits 0.
  * It binds ONLY a loopback address (127.0.0.1 / ::1 / localhost). A public bind such as
    0.0.0.0 is REFUSED (exit 2) until a future, separate task explicitly approves it.
  * It uses a fresh temp DB by default and never touches the production DB.
  * It creates no systemd unit, no nginx config, and no TLS. It is an operator convenience only.

This is intentionally a developer tool. Stop it with Ctrl-C.
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import db as dbmod, migrate, portal_http, seed  # noqa: E402

_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}


def _is_loopback(host: str) -> bool:
    return host in _LOOPBACK_HOSTS


def _make_handler(app: portal_http.PortalHttpApp):
    class _Handler(BaseHTTPRequestHandler):
        # Silence the default stderr logging; we emit sanitized lines ourselves.
        def log_message(self, *args, **kwargs):  # noqa: D401
            return

        def _serve(self, method: str) -> None:
            request = portal_http.HttpRequest.build(
                method,
                self.path,
                headers={k: v for k, v in self.headers.items()},
                remote_addr=self.client_address[0] if self.client_address else None,
            )
            response = app.handle(request)
            sys.stdout.write(app.access_line(request, response) + "\n")
            sys.stdout.flush()
            body = response.body.encode("utf-8")
            self.send_response(response.status_code)
            self.send_header("Content-Type", response.content_type)
            for name, value in response.headers.items():
                self.send_header(name, value)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if method != "HEAD":
                self.wfile.write(body)

        def do_GET(self):  # noqa: N802
            self._serve("GET")

        def do_HEAD(self):  # noqa: N802
            self._serve("HEAD")

    return _Handler


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Loopback-only portal preview server (operator tool).")
    ap.add_argument("--serve-local", action="store_true",
                    help="REQUIRED to actually bind. Without it, nothing is started.")
    ap.add_argument("--host", default="127.0.0.1", help="Loopback host only (default 127.0.0.1).")
    ap.add_argument("--port", type=int, default=8088, help="Loopback port (default 8088).")
    ap.add_argument("--db", help="Optional temp DB path. Defaults to a fresh temp DB.")
    args = ap.parse_args(argv)

    if not args.serve_local:
        print("Preview server NOT started. Re-run with --serve-local to bind a loopback port.")
        print("This tool refuses public binds and creates no systemd/nginx/TLS.")
        return 0

    if not _is_loopback(args.host):
        print(f"REFUSED: host '{args.host}' is not loopback. Public binds are not allowed in this phase.",
              file=sys.stderr)
        return 2

    db_path = args.db or os.path.join(tempfile.mkdtemp(prefix="unseen_preview_"), "portal.sqlite3")
    migrate.migrate_path(db_path)
    conn = dbmod.connect(db_path)
    seed.seed(conn)
    app = portal_http.PortalHttpApp(conn)

    server = HTTPServer((args.host, args.port), _make_handler(app))
    print(f"Loopback preview on http://{args.host}:{args.port} (temp DB; Ctrl-C to stop).")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

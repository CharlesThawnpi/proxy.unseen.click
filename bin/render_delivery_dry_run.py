#!/usr/bin/env python3
"""Render a delivery preview + sanitized Hiddify-output summary (DRY-RUN; NO network, NO links).

Normalizes a MOCKED Hiddify subscription output to a sanitized summary and prints the Burmese
delivery preview that a customer would see — with NO raw link/token/QR. Useful for eyeballing the
delivery copy without any node connection.

  python3 bin/render_delivery_dry_run.py
  python3 bin/render_delivery_dry_run.py --output-json @/path/to/mock.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import hiddify_subscription_output as hout, qr_renderer, telegram_messages as msg  # noqa: E402

_SAMPLE = {
    "all_configs": [
        {"protocol": "hysteria2", "name": "FAST1"},
        {"protocol": "shadowsocks", "name": "FAST2"},
        {"protocol": "vless-reality", "name": "Secure"},
    ],
    "deep_link": "hiddify://import/EXAMPLE-PLACEHOLDER",
}


def _load(spec: str):
    if not spec:
        return _SAMPLE
    if spec.startswith("@"):
        with open(spec[1:], encoding="utf-8") as fh:
            return json.load(fh)
    return json.loads(spec)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Render delivery preview from mocked Hiddify output.")
    ap.add_argument("--output-json", default="", help="JSON string or @file; default built-in sample")
    args = ap.parse_args(argv)

    summary = hout.normalize(_load(args.output_json))
    qr = qr_renderer.qr_plan()
    copy_avail = summary.has_subscription_url or summary.has_deep_link
    print("=== sanitized Hiddify output summary ===")
    print(json.dumps(summary.as_dict(), ensure_ascii=False, indent=2))
    print(f"\n=== QR capability ===\n{qr.status}: {qr.note}")
    print("\n=== delivery preview (Burmese; no link/token/QR) ===")
    print(msg.delivery_preview(summary.has_deep_link, copy_avail, qr.available))
    print("\nRENDER_DRY_RUN_OK: sanitized; no raw links; no network.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

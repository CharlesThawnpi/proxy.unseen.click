#!/usr/bin/env python3
"""Scan source/docs for legacy timestamp patterns. No DB access, no network, sanitized paths only."""
from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DIRS = ("backend", "bin", "docs", "tests")
PATTERNS = {
    "python_now": re.compile(r"\bdatetime\.(now|utcnow)\s*\("),
    "sqlite_now": re.compile(r"datetime\('now'\)|CURRENT_TIMESTAMP"),
    "timestamp_fields": re.compile(
        r"\b(approved_at|start_date|expiry_date|sent_at|next_attempt_at|created_at|updated_at|"
        r"expires_at|revoked_at|last_verified_at|consumed_at|raised_at|cleared_at|performed_at|ts)\b"
    ),
}


def _iter_files(paths: list[str]):
    for raw in paths:
        base = (ROOT / raw).resolve()
        if not (base == ROOT or ROOT in base.parents):
            continue
        if base.is_file():
            yield base
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.suffix in {".py", ".md", ".sql", ".sh"}:
                if any(part in {"tmp", "logs", "backups", "data", "__pycache__"} for part in path.parts):
                    continue
                yield path


def scan(paths: list[str]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for path in sorted(set(_iter_files(paths))):
        text = path.read_text(encoding="utf-8", errors="ignore")
        hits = {name: len(pattern.findall(text)) for name, pattern in PATTERNS.items()}
        hits = {k: v for k, v in hits.items() if v}
        if hits:
            out[str(path.relative_to(ROOT))] = hits
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Audit timestamp patterns (sanitized summary only).")
    ap.add_argument("paths", nargs="*", default=list(DEFAULT_DIRS))
    args = ap.parse_args(argv)
    results = scan(args.paths)
    print("timestamp_audit")
    for path, hits in results.items():
        total = sum(hits.values())
        kinds = ",".join(f"{k}:{v}" for k, v in sorted(hits.items()))
        print(f"{path} total:{total} {kinds}")
    print(f"files_with_hits={len(results)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

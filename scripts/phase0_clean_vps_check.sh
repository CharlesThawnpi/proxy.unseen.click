#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/unseen-proxy"
OUT="$ROOT/docs/CLEAN_VPS_CHECKLIST.md"
TS="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

mkdir -p "$ROOT/docs"

{
  echo "# CLEAN VPS CHECKLIST"
  echo
  echo "- Checked at UTC: $TS"
  echo "- Hostname: $(hostname)"
  echo "- Project root: $ROOT"
  echo
  echo "## Scope check"
  test -d "$ROOT" && echo "- PASS: project root exists" || echo "- FAIL: project root missing"
  echo
  echo "## Legacy artifact scan"
  echo "This scan is report-only. Do not delete anything automatically."
  echo
  echo '```text'
  find /opt /etc/systemd/system /etc/nginx /var/www /root -maxdepth 4 \
    \( -iname '*unseenvpn*' -o -iname '*marzban*' -o -iname '*happ*' \) \
    2>/dev/null || true
  echo '```'
  echo
  echo "## Git status"
  echo '```text'
  if command -v git >/dev/null 2>&1 && git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    git -C "$ROOT" status --short
  else
    echo "Git repo not initialized yet."
  fi
  echo '```'
  echo
  echo "## Result"
  echo "- Status: REVIEW_REQUIRED"
  echo "- Operator must confirm no legacy artifacts before Phase 1 implementation."
} > "$OUT"

echo "Wrote $OUT"

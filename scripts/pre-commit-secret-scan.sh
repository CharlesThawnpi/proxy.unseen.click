#!/usr/bin/env bash
#
# UNSEEN PROXY — pre-commit secret scan (IMPLEMENTATION_PLAN.md §31, §31A.3)
#
# Operationalizes the standing rule "secrets never enter git" so it cannot be
# violated by accident. Scans STAGED changes only and:
#   - HARD-BLOCKS the commit on forbidden paths (.env, DBs, keys, runtime dirs).
#   - HARD-BLOCKS the commit on secret-shaped CONTENT (real tokens/keys/URIs).
#   - WARNS (never blocks) on full IPv4 addresses — the server inventory in the
#     plan and docs/SERVERS.md legitimately records them; §31's "no full IPs"
#     rule targets runtime logs/errors, not the architecture inventory.
#
# Design notes:
#   - Content patterns require a REAL payload, so documentation placeholders
#     (`<token>`, `__PLACEHOLDER__`, `hiddify://import/<sub-link>`) do NOT trip
#     them — only concrete secrets do.
#   - Patterns embed character-classes so this scanner does not match its own
#     source. It is therefore scanned like any other file (no self-exclusion).
#
# Exit 0 = clean (commit proceeds). Exit 1 = blocked (commit aborts).

set -euo pipefail

fail=0

# ---- helpers ---------------------------------------------------------------

block() { printf '  \033[31mBLOCK\033[0m  %s\n' "$1" >&2; fail=1; }
warn()  { printf '  \033[33mWARN \033[0m  %s\n' "$1" >&2; }

# Staged files that are Added or Modified (skip deletions/renames-source).
mapfile -t staged < <(git diff --cached --name-only --diff-filter=AM)

if [ "${#staged[@]}" -eq 0 ]; then
  exit 0
fi

# ---- 1. forbidden PATHS (never tracked, regardless of content) -------------

for f in "${staged[@]}"; do
  case "$f" in
    .env|.env.*)
      [ "$f" = ".env.example" ] || block "forbidden path staged (secret env file): $f" ;;
  esac
  case "$f" in
    *.sqlite3|*.sqlite3-*|*.db|*.db-*)        block "forbidden path staged (database): $f" ;;
    data/*|backups/*|logs/*|tmp/*)            block "forbidden path staged (runtime/state dir): $f" ;;
    *.key|*.pem|*.crt|*.p12|*.pfx)            block "forbidden path staged (key/cert material): $f" ;;
    *.qr.png|*.qr.svg)                        block "forbidden path staged (generated QR payload): $f" ;;
    screenshots/*|uploads/*|receipts/generated/*|invoices/generated/*)
                                              block "forbidden path staged (generated/private payload): $f" ;;
  esac
done

# ---- 2. secret-shaped CONTENT in staged blobs ------------------------------

# Lines matching this are treated as placeholders/examples and skipped.
placeholder='(__PLACEHOLDER__|<[^>]+>|CHANGEME|changeme|your[-_]|example|EXAMPLE|xxxx|XXXX|\.\.\.|placeholder)'

# Secret CONTENT patterns (each requires a concrete payload).
PEM='BEGIN[A-Z ]*PRIVATE KEY'                                   # PEM private key header
BOTTOK='[0-9]{8,10}:[A-Za-z0-9_-]{35}'                          # Telegram bot token shape
SUBTOK='sub\.[A-Za-z0-9.]+/s/[A-Za-z0-9_-]{16,}'               # real subscription token URL
PROXYURI='(vless|vmess|trojan|ss|hy2|hysteria2)://[A-Za-z0-9+/=._:@%-]{20,}'  # real config URI w/ payload
SECRETASSIGN='(SECRET|TOKEN|PASSWORD|API_KEY|PRIVATE_KEY|ENCRYPTION_SECRET)[A-Z_]*[[:space:]]*[:=][[:space:]]*["'"'"']?[A-Za-z0-9+/=]{16,}'

for f in "${staged[@]}"; do
  # Only scan text blobs; skip anything git sees as binary.
  if ! git show ":$f" 2>/dev/null | grep -Iq . ; then
    continue
  fi
  content="$(git show ":$f" 2>/dev/null || true)"

  # Strip placeholder lines before the secret-content scan (avoids false positives).
  scanme="$(printf '%s\n' "$content" | grep -Ev "$placeholder" || true)"

  printf '%s\n' "$scanme" | grep -Eq "$PEM"          && block "PEM private key material in: $f"
  printf '%s\n' "$scanme" | grep -Eq "$BOTTOK"       && block "Telegram-bot-token shape in: $f"
  printf '%s\n' "$scanme" | grep -Eq "$SUBTOK"       && block "subscription token URL in: $f"
  printf '%s\n' "$scanme" | grep -Eq "$PROXYURI"     && block "concrete proxy config URI in: $f"
  printf '%s\n' "$scanme" | grep -Eq "$SECRETASSIGN" && block "assigned secret value (non-placeholder) in: $f"

  # Full IPv4 — warn only, and not for markdown docs (inventory lives there).
  case "$f" in
    *.md) : ;;
    *)
      if printf '%s\n' "$content" | grep -Eoq '([0-9]{1,3}\.){3}[0-9]{1,3}'; then
        warn "full IPv4 address present in $f (allowed, but confirm it is inventory, not runtime data)"
      fi ;;
  esac
done

# ---- result ----------------------------------------------------------------

if [ "$fail" -ne 0 ]; then
  printf '\n\033[31mpre-commit secret scan FAILED\033[0m — commit aborted.\n' >&2
  printf 'Remove the flagged secret/path from the staged set. If a secret was already committed,\n' >&2
  printf 'treat it as an incident: rotate it (docs/SECRET_ROTATION.md), do not just amend.\n' >&2
  exit 1
fi

exit 0

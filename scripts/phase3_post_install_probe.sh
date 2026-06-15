#!/usr/bin/env bash
#
# UNSEEN PROXY — Phase 3 post-install READ-ONLY probe (sanitized).
#
# Run this AFTER Hiddify is installed (operator runs the install per
# docs/PHASE3_HIDDIFY_LIVE_VERIFY.md). It collects the facts needed to fill the
# verified Hiddify contract WITHOUT exposing any secret.
#
# It is strictly read-only: it inspects containers/ports/units/firewall/resources.
# It NEVER reads Hiddify config files, the admin proxy path, API key/UUID, Reality
# keys, or subscription links — so its output is safe to paste into a doc/PR.
#
# Usage: bash scripts/phase3_post_install_probe.sh
set -euo pipefail

line() { printf '\n===== %s =====\n' "$1"; }

line "TIMESTAMP / HOST"
date -u +"%Y-%m-%dT%H:%M:%SZ"; hostname

line "SSH STILL LISTENING (must be present)"
ss -tlnp 2>/dev/null | grep -E ':22\b' || echo "WARNING: SSH:22 not listening!"

line "DOCKER CONTAINERS (names/images/ports — not secrets)"
command -v docker >/dev/null 2>&1 && docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' || echo "docker not present"

line "DOCKER IMAGES (for version pinning)"
command -v docker >/dev/null 2>&1 && docker images --format '{{.Repository}}:{{.Tag}}  {{.ID}}' | grep -i hiddify || echo "(no hiddify images / docker absent)"

line "LISTENING PORTS (record panel/sub/proxy ports; these are not secrets)"
ss -tulpn 2>/dev/null

line "HIDDIFY / DOCKER SYSTEMD UNITS"
systemctl list-units --type=service --no-legend --no-pager 2>/dev/null | grep -Ei 'hiddify|docker' || echo "(none)"

line "FIREWALL: iptables policies + rule COUNT (not dumping rule bodies)"
echo "INPUT policy: $(iptables -S 2>/dev/null | grep -m1 '^-P INPUT' || echo '?')"
echo "rule count:   $(iptables -S 2>/dev/null | grep -c '^-A' || echo '?')"
echo "ufw: $(ufw status 2>/dev/null | head -1)"
echo "nft ruleset lines: $(nft list ruleset 2>/dev/null | wc -l)"

line "RESOURCE USAGE (compare to pre-install baseline in the live-verify doc)"
free -h | head -2; df -h / | tail -1

line "REMINDER"
cat <<'EOF'
Do NOT paste any of the following into git/docs/chat:
  - the Hiddify admin link / admin_proxy_path / API key (admin UUID)
  - any user UUID, subscription URL, hiddify://, vless://, ss://, hy2:// link
  - Reality private keys / short-ids, QR payloads
Record only: version, ports, container/unit names, firewall rule COUNTS, resource deltas.
Real secrets (admin UUID/path) go ONLY into a root-owned 0600 file outside git; document the path pattern, not the value.
EOF

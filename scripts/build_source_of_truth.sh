#!/usr/bin/env bash
#
# UNSEEN PROXY — build SOURCE_OF_TRUTH.md
#
# Assembles ONE consolidated, current "source of truth" file for an external reader
# (e.g. Charles's Custom GPT instruction field). It is DERIVED from the canonical
# living docs, so it stays in sync: re-run this after any task, commit the result,
# then download SOURCE_OF_TRUTH.md from GitHub and re-upload it to the GPT.
#
# Why not IMPLEMENTATION_PLAN.md? That is the static v1.9 *plan* (intent/spec). It is
# intentionally NOT edited as work proceeds — execution reality lives in CURRENT_STATUS,
# DECISIONS (ADRs that supersede the plan), CHANGELOG, and the verified contracts.
# SOURCE_OF_TRUTH.md merges the plan's invariants with that live state.
#
# Secret-safe: it only concatenates already-committed, secret-free docs. No secrets here.

set -euo pipefail
ROOT="/opt/unseen-proxy"
OUT="$ROOT/SOURCE_OF_TRUTH.md"
TS="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
cd "$ROOT"

sec() { printf '\n\n---\n\n# %s\n\n' "$1" >> "$OUT"; }

{
  echo "# UNSEEN PROXY — SOURCE OF TRUTH (consolidated, auto-generated)"
  echo
  echo "> **Generated:** $TS — by \`scripts/build_source_of_truth.sh\`."
  echo "> **This is the live project state for external readers (e.g. the Custom GPT).** It is DERIVED from the"
  echo "> canonical docs below and regenerated each task. Upload THIS file to the GPT (not IMPLEMENTATION_PLAN.md,"
  echo "> which is the static v1.9 plan). Re-download after updates."
  echo
  echo "## How the canonical docs relate"
  echo "- \`IMPLEMENTATION_PLAN.md\` — static v1.9 **plan/intent** (not updated as work proceeds)."
  echo "- \`docs/DECISIONS.md\` — **ADRs that SUPERSEDE the plan** where they differ (authoritative)."
  echo "- \`docs/CURRENT_STATUS.md\` — **live phase tracker + next task**."
  echo "- \`docs/TIMEZONE_POLICY.md\` — **project-wide business/customer timezone rule**."
  echo "- \`docs/CHANGELOG.md\` — chronological record of what changed."
  echo "- \`docs/HIDDIFY_API_CONTRACT.md\` — verified Hiddify API v2 contract."
  echo "- Other \`docs/*.md\` — architecture, security, nodes, regions, protocols, etc."
  echo
  echo "## Non-negotiable invariants (from the plan + ADRs)"
  echo "- **Clean-build isolation:** build only from this project; never reference the retired UNSEEN VPN/Marzban/Happ."
  echo "- **Master = control-plane only;** it carries NO proxy traffic (co-location RETIRED — ADR-001)."
  echo "- **Dynamic config:** plans/prices/caps/durations/regions/protocols/nodes are DB-driven, never hardcoded."
  echo "- **Secrets never exposed/committed;** \`.env\` only, git-ignored + pre-commit secret scan."
  echo "- **Not all regions/protocols live by default;** each enabled only after a node test. Nodes start \`status=test\`."
  echo "- **Dry-run first; live actions double-gated** (env latch + \`--live --confirm\`). Never fabricate a PASS."
  echo "- **Hiddify uses GB**; UNSEEN stores GiB — convert GiB↔GB at the orchestrator."
  echo "- **Burmese-primary frontend** (~90% Burmese / English terms); invoices/receipts in English; no email/password."
  echo "- **Business/customer dates use Myanmar Time:** MMT, UTC+06:30, \`Asia/Yangon\`; external UTC converts at the boundary."
} > "$OUT"

sec "CURRENT STATUS (docs/CURRENT_STATUS.md)";        cat docs/CURRENT_STATUS.md          >> "$OUT"
sec "TIMEZONE POLICY (docs/TIMEZONE_POLICY.md)";      cat docs/TIMEZONE_POLICY.md        >> "$OUT"
sec "DECISIONS / ADRs (docs/DECISIONS.md)";           cat docs/DECISIONS.md               >> "$OUT"
sec "VERIFIED HIDDIFY API CONTRACT (head of docs/HIDDIFY_API_CONTRACT.md)"
sed -n '1,60p' docs/HIDDIFY_API_CONTRACT.md          >> "$OUT"
sec "RECENT CHANGELOG (head of docs/CHANGELOG.md)"
sed -n '1,90p' docs/CHANGELOG.md                     >> "$OUT"
sec "SERVER / NODE INVENTORY (head of docs/SERVERS.md)"
sed -n '1,60p' docs/SERVERS.md                       >> "$OUT"

printf '\n\n---\n\n_End of consolidated source of truth. Regenerate with \`bash scripts/build_source_of_truth.sh\`._\n' >> "$OUT"
echo "Wrote $OUT ($(wc -l < "$OUT") lines)"

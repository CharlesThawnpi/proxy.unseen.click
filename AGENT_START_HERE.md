# AGENT START HERE — UNSEEN PROXY

You are working on the new UNSEEN PROXY project only.

Canonical source of truth:
- IMPLEMENTATION_PLAN.md
- Project root: /opt/unseen-proxy/

Hard rules:
1. Build only from IMPLEMENTATION_PLAN.md.
2. Do not search, import, clone, compare against, or reference any retired UNSEEN VPN / Marzban / Happ artifact.
3. Do not build outside /opt/unseen-proxy/.
4. Do not create real services, DB mutations, Hiddify calls, payments, bot sends, or node changes unless the current phase explicitly allows it.
5. Never print or commit secrets, tokens, subscription links, QR payloads, .env values, private keys, node API keys, panel admin paths, full IPs, payment refs, or private customer data.
6. Use .env.example placeholders only.
7. Every change must update docs under /opt/unseen-proxy/docs/.
8. Never report PASS unless verified on disk or by a local command.
9. First task is Phase 0 + Phase 1 only.

Current phase (see docs/CURRENT_STATUS.md for the live tracker):
- Phase 0: Clean-VPS verification — DONE (gate PASS, signed off in docs/CLEAN_VPS_CHECKLIST.md).
- Phase 1: Documentation, repo, architecture skeleton — DONE (docs/ skeleton per §32, git repo + secret-scan hook, .env.example).
- Next: Phase 2 — disposable DE Hiddify test node (no node exists yet; per-node clean-check is signed off there before use).

Key docs: docs/CURRENT_STATUS.md (phase tracker), docs/VERSION_CONTROL.md + docs/DEPLOYMENT.md (git/deploy),
docs/SECURITY.md (the 10 non-negotiable rules), docs/CHANGELOG.md.

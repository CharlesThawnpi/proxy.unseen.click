# BRAIN API — design (read-only project-state endpoint for the Custom GPT)

> **Status: DESIGN ONLY (ADR decision 2026-06-16). NOT built/deployed.** Build is a separate gated task.
> Purpose: let Charles's Custom GPT fetch **current, sanitized project state** (as a GPT *Action*) before drafting
> task prompts — the live equivalent of downloading `SOURCE_OF_TRUTH.md`.

## Why design-first
A GPT Action calls an **authenticated public HTTPS endpoint**. Standing that up on the **protected, control-plane-only
Master** is a new outward-facing service (TLS + auth + attack surface) not in the plan. So we design it now and build
it deliberately later, hardened. Until then the GPT uses the downloadable `SOURCE_OF_TRUTH.md`.

## Principles (hard requirements for the future build)
- **Read-only.** No mutations, ever. No node management, no provisioning, no DB writes.
- **Sanitized-only output.** Exposes the same class of content as `SOURCE_OF_TRUTH.md` — phase/status, decisions,
  verified contract shape, node *status* (alias/region/status/verification), pending follow-ups. **Never** secrets:
  no API keys, admin proxy paths, UUIDs, subscription/proxy links, IPs beyond the already-published inventory, no PII.
- **Authenticated.** Bearer token (`Authorization: Bearer <token>`) stored in `.env` on the Master, configured in the
  GPT Action's auth. Rotatable. Rate-limited. (OpenAI egress IPs vary, so token-auth, not IP allowlist.)
- **Own subdomain + TLS,** e.g. `brain.unseen.click` (or a path under `api.unseen.click`), nginx-fronted, loopback app.
- **Minimal + isolated.** A tiny stdlib (or FastAPI) service bound to loopback; nginx terminates TLS. Lives behind the
  same gated/dry-run culture; no coupling to live provisioning.
- **Derived from the same canonical docs** the SOURCE_OF_TRUTH generator uses — single source, two surfaces (file + API).

## Proposed surface (v0, read-only)
| Method | Path | Returns |
|---|---|---|
| GET | `/v1/health` | `{status:"ok", ts}` (no auth) |
| GET | `/v1/state` | consolidated JSON: phase, current_status summary, decisions (ADR list), next task, node statuses (sanitized) |
| GET | `/v1/contract/hiddify` | the VERIFIED-LIVE Hiddify contract summary (endpoints/fields/units) — no secrets |
| GET | `/v1/changelog?limit=N` | recent changelog entries |

- Response: JSON; an OpenAPI 3.1 schema is published for the GPT to import as an Action.
- All payloads are generated from `docs/` (CURRENT_STATUS, DECISIONS, HIDDIFY_API_CONTRACT, CHANGELOG, SERVERS) +
  read-only DB queries for **non-sensitive** node/plan status (e.g. counts, statuses) — never raw rows with secrets.

## Build checklist (future gated task)
1. Write the OpenAPI 3.1 schema for the GPT Action.
2. Implement a loopback read-only service (stdlib `http.server` or FastAPI) sourcing from the canonical docs/DB views.
3. nginx vhost + TLS (Certbot) for `brain.unseen.click`; bearer-token auth; rate limit; `access_log` minimal.
4. Secret-scan responses (assert no secret-shaped strings can be emitted).
5. Tests: auth required; no secret in any response; read-only (no mutating routes exist).
6. Document deploy + token rotation in DEPLOYMENT/SECURITY.

## Interim (now)
Use **`SOURCE_OF_TRUTH.md`** (repo root, regenerated each task via `scripts/build_source_of_truth.sh`): download from
GitHub → upload to the GPT instruction field. The Brain API later automates this "freshness" without manual download.

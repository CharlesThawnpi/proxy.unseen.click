# CURRENT STATUS

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §34
> **Status:** live phase tracker; updated as phases progress

Where the UNSEEN PROXY build stands across the §34 deployment phases.

## Phase tracker

| Phase | Title | Status |
|---|---|---|
| 0 | Clean-VPS verification (gate before any build) | DONE (gate passed) |
| 1 | Documentation, repo & architecture planning | DONE (pushed to origin/main, 25e5ddc) |
| 2 | Hiddify test VPS setup (Master/DE co-located) | **PREFLIGHT DONE — install on HOLD** (see PHASE2_MASTER_DE_HIDDIFY_PREFLIGHT.md) |
| 3 | Hiddify API & subscription compatibility audit | PENDING |
| 4 | Database & backend clone design | PENDING |
| 5 | Telegram bot implementation (Burmese-primary) | PENDING |
| 6 | Hiddify subscription delivery integration | PENDING |
| 7 | Plan-based region/protocol entitlement + node resilience | PENDING |
| 8 | Web app / customer portal | PENDING |
| 9 | Messenger and Viber bot integration | PENDING |
| 10 | Monitoring, backup, security, production hardening | PENDING |
| 11 | Internal beta testing | PENDING |
| 12 | Controlled public soft launch | PENDING |

## Next up

The DE node is **co-located on the Master** (§4.1 exception), so it is **not disposable** — the standard
"wipe freely" rule does not apply. The protected preflight is complete with a **PARTIAL / HOLD** readiness
decision: install must not proceed until (B1) the 80/443 + TLS coexistence strategy is decided, (B2) Charles
takes & confirms a provider snapshot, (B3) a firewall/exposure plan exists, and (B4) the Phase 3 Hiddify
port/API audit is done. Details + risks in `PHASE2_MASTER_DE_HIDDIFY_PREFLIGHT.md`.

**Next task:** Phase 3 — read-only Hiddify API & port/TLS audit (produces the verified `HIDDIFY_API_CONTRACT.md`),
and in parallel Charles takes the Master provider snapshot. Only then is the protected co-located install authorized.
The node will be created as `status=test` and never auto-promoted to `live`.

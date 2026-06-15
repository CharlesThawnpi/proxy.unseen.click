# SECRET ROTATION

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §30A.5
> **Status:** Phase 1 skeleton — stub; verified in Phase 10

§30A.5 defines a **no-downtime rotation runbook** for the two classes of long-lived secret:

- **`ACCESS_TOKEN_ENCRYPTION_SECRET`** — re-encrypt each token payload old→new, bumping `token_storage_version`, holding both secrets during the transition.
- **Node API keys** — issue a new least-privilege key, update the node's `.env` handle on the Master, verify a read-only probe, then revoke the old key.

Rotation is a gated/latched operation (env latch + `--live --confirm`), backed up before and verified after with a no-send token-decrypt smoke test.

> Verified in Phase 10

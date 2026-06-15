# SECURITY

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §31, §30A.5, §31A
> **Status:** Phase 1 skeleton — decided from plan

The non-negotiable security and secret-safety rules for UNSEEN PROXY. These are enforced in code review and in the agent's behavior; violating one is a defect.

## The 10 non-negotiable rules (§31)

1. **Never expose secrets.** No tokens, token hashes, subscription URLs, QR payloads, deep links containing tokens, API keys, panel admin paths, panel/admin credentials, Reality private keys/short-ids, or customer PII in logs, errors, audit entries, commits, chat output, or third-party calls. Print only **fingerprints** and **masked IPs**.
2. **Durable tokens are encrypted at rest** with `ACCESS_TOKEN_ENCRYPTION_SECRET`. Raw tokens are never stored; URLs/QRs are built in memory and never persisted.
3. **No third-party exfiltration.** Subscription URLs/tokens are never submitted to external services. Submitting a sub URL to an external "crypt" service counts as exfiltration and is hard-blocked. Any crypto/obfuscation is done locally or out-of-band.
4. **Do not hardcode business values.** Plans, prices, caps, durations, device counts, region lists, and protocol labels all come from the DB.
5. **Not all regions/protocols live by default.** Each is enabled explicitly after a node test.
6. **No risky protocol/routing changes without testing** on a disposable target first.
7. **Honest promises only.** Never tell users configs are impossible to copy/share. Lean on per-user tokens, caps, expiry, rotation, UA-filter, and leak monitoring.
8. **Least-privilege node API keys.** Panel admin paths and ports are not public; consider IP-allowlisting the web admin.
9. **`.env` files are `0600`, root-owned; secrets never enter git** (enforced by `.gitignore` + a pre-commit secret scan, §31A). Use `.env.example` with placeholder keys.
10. **Never fabricate a PASS.** Always verify artifacts exist on disk / endpoints actually return the expected status before reporting success. Fail closed and say so honestly when blocked.

## Secret-safety posture

- **Fingerprints + masked IPs only.** Sanitized-by-construction logging (§30.1): subscription/sidecar logs carry fingerprint + status + body length + UA class + masked IP prefix — never raw token/URL/body/full IP/PII.
- **Durable tokens encrypted at rest.** Encryption uses `ACCESS_TOKEN_ENCRYPTION_SECRET`; losing it makes tokens undecryptable (see [BACKUPS.md](BACKUPS.md)). Raw tokens are never stored.
- **No third-party exfiltration** of subscription URLs or tokens (rule 3).
- **Least-privilege node API keys** (rule 8); admin paths/ports stay non-public.
- **Never fabricate a PASS** (rule 10) — fail closed and report honestly when blocked.

## Secret rotation (§30A.5)

A no-downtime rotation runbook exists for the two long-lived secret classes — `ACCESS_TOKEN_ENCRYPTION_SECRET` (re-encrypt token payloads old→new, bumping `token_storage_version`, both secrets held during transition) and node API keys (issue new least-privilege key, verify read-only probe, revoke old). Rotation is gated/latched (env latch + `--live --confirm`), backed up before and verified after. See [SECRET_ROTATION.md](SECRET_ROTATION.md).

## Secret-scan in git (§31A)

`.gitignore` plus a pre-commit hook scan staged changes for secret-shaped strings and block the commit if any are found. A committed secret is a **security incident**: rotate the exposed secret (§30A.5), don't just delete the commit. See [VERSION_CONTROL.md](VERSION_CONTROL.md).

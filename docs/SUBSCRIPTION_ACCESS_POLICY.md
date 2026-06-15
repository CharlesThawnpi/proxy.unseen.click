# SUBSCRIPTION ACCESS POLICY — Token, sidecar & UA filter

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §17 (17.1, 17.3), §31
> **Status:** Phase 1 skeleton — decided from plan
> **Sidecar implementation Verified in Phase 6**

How a customer's subscription is addressed by an opaque per-customer token, served through the UNSEEN-branded sidecar, and protected by a User-Agent filter — with secret-safety rules that are non-negotiable.

## Per-customer opaque token model (§17.3)

Per-customer opaque token: `secrets.token_urlsafe(32)`, stored as:

| Field | Purpose |
|---|---|
| `token_hash` | SHA-256 of the token, unique lookup key |
| `token_fingerprint` | first 8 hex of the hash, for logs |
| `encrypted_token_payload` | durable upstream reference, decryptable **only** with `.env` `ACCESS_TOKEN_ENCRYPTION_SECRET` |
| `customer_id` / `profile_id` / `subscription_id` | ownership |
| `purpose`, `status` (`active`/`revoked`/`rotated`/`expired`), `expires_at`, rotation lineage | lifecycle |

**Rules:** the **raw token is never stored plaintext**; the URL/QR are built **only in memory**. Manager CLI `public_token_manager.py`: `issue | list | verify | rotate | revoke | preflight`, gated for live writes.

## UNSEEN-branded sidecar (§17.1)

A thin WSGI service at **`sub.unseen.click/s/<token>`** (placeholder form — never a real token). On `GET /s/<token>`:

1. **UA-filter first** (before token resolution) — see below.
2. **SHA-256 the token**; resolve to a customer + entitlement set; **fail-closed** (uniform 404) on unknown/revoked/expired.
3. **Decrypt** the per-customer token's stored upstream reference **in memory** (never logged).
4. **Fetch upstream** the entitled region(s)' Hiddify subscription content and merge.
5. **Filter by entitlement** (region **and** protocol) — fail-closed: drop entries the plan does not allow or that are unknown/unmappable.
6. **Re-brand**: profile title `UNSEEN PROXY | <public_customer_code>`, support URL, update interval, optional `hide-settings` headers as **deterrence only — never claimed as encryption**.
7. **Serve**; log **only**: token **fingerprint** (8 hex), status, body length, UA class, **masked IP prefix** (/24, /48). Never the raw token, URL, body, or full IP. The `/s/` location has `access_log off`.

## User-Agent filter

- Modes: **off / report / enforce**.
- **Allowlist of real clients** must include: `hiddify`, `hiddifynext`, sing-box, clash/mihomo/meta, v2ray, nekobox, streisand, shadowrocket, karing, etc.
- Browsers / curl / empty UA → **reason-opaque 404** (this is the expected, documented browser-block behavior; the subscription URL only works inside the Hiddify App).
- Configured via the systemd unit `Environment=` (overrides any code default); an internal health-check UA is allowlisted and excluded from the leak-watcher.

## Secret-safety rules (§31, non-negotiable)

1. **Never expose secrets** — no tokens, token hashes, subscription URLs, QR payloads, deep links containing tokens, API keys, panel admin paths/credentials, Reality keys, or PII in logs, errors, audit entries, commits, chat output, or third-party calls. Print only **fingerprints** and **masked IPs**.
2. **Durable tokens are encrypted at rest** with `ACCESS_TOKEN_ENCRYPTION_SECRET`; **raw tokens never stored**; URLs/QRs built in memory and never persisted.
3. **No third-party exfiltration** — never submit subscription URLs/tokens to external services; any crypto/obfuscation is local or out-of-band.
4. **Honest promises only** — never tell users configs are impossible to copy/share. Lean on per-user tokens, caps, expiry, rotation, the UA-filter, and leak monitoring.

> Delivery records are metadata-only (`secret_payload_stored = 0`, enforced by a CHECK constraint).

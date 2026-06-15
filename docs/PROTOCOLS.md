# PROTOCOLS

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §3.2, §26
> **Status:** Phase 1 skeleton — decided from plan

The mapping between user-facing profile names and the underlying engine protocols.

> **This is the ONLY document where technical protocol names appear.** Everywhere else (bot menus, portal, sidecar branding) uses the user-facing labels only. The number-dropping display rule and the technical names stay here.

## Profile ↔ protocol mapping

| User label | Protocol (admin only) | Role | Hiddify support |
|---|---|---|---|
| **FAST1** | **Hysteria2** | Default, fastest, best on lossy links | Native |
| **FAST2** | **Shadowsocks** | Secondary fast | Native |
| **Secure** | **VLESS-Reality** | Stealth/secure; may be plan-gated | Native |

- `profiles` maps `profile_code (FAST1/FAST2/SECURE) → protocol_code`.
- The sidecar classifies each upstream entry by protocol and keeps it **only if** entitled **and** active **and** available on that node — fail-closed for unknown protocols.

## The "Fast" display rule (computed at render time)

The DB stores canonical codes (`FAST1`, `FAST2`) and a base label. The presentation layer applies one rule:
- If the plan entitles **only one** Fast tier → render it as **"Fast"** (drop the number).
- If it entitles **both** → render **"Fast1"** and **"Fast2"**.
- **Secure** always renders as "Secure".

So TRIAL/BASIC/CORE show a clean **Fast + Secure**, while PLUS/PRO/MAX show **Fast1 + Fast2 + Secure** — all from the same data. Re-labeling the base text is a DB field; the drop-the-number behavior is logic.

## Per-plan entitlement seed

| Plan | FAST1 (Hysteria2) | FAST2 (Shadowsocks) | Secure (VLESS-Reality) | Renders as |
|---|---|---|---|---|
| TRIAL | yes | — | yes | Fast, Secure |
| BASIC | yes | — | yes | Fast, Secure |
| CORE | yes | — | yes | Fast, Secure |
| PLUS | yes | yes | yes | Fast1, Fast2, Secure |
| PRO | yes | yes | yes | Fast1, Fast2, Secure |
| MAX | yes | yes | yes | Fast1, Fast2, Secure |

## Default exposure for v1

- **FAST1 (Hysteria2) is the default profile on every plan**; Secure (VLESS-Reality) always available.
- **FAST2 (Shadowsocks) is fully wired for PLUS/PRO/MAX** and goes live as soon as its inbound passes the node test gate.
- **Do not enable a protocol on the sidecar before its inbound is live and tested on the node.** Until then the sidecar fails closed and the profile does not appear even for entitled plans.

> Node inbound test gate: Verified in Phase 3.

# NETWORK

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §4, §5, §6, §8
> **Status:** Phase 1 skeleton — decided from plan

How traffic flows and how Master services are exposed.

## Loopback-binding discipline

Every Master service binds to `127.0.0.1` on its own loopback port (see [PORTS.md](PORTS.md)). No application service listens on a public interface. This keeps the public attack surface to nginx alone.

## nginx is the sole owner of :80 / :443

On the Master, **nginx is the only process bound to public `:80` and `:443`**. It terminates TLS (Let's Encrypt / Certbot) and routes by subdomain to the appropriate loopback service. The `/s/` location (subscription delivery) has `access_log off` so tokens never leak to disk.

## Control-plane vs data-plane traffic

- **Control-plane traffic** is Master → node management over HTTPS **API v2** (create/update/disable users, read usage). This is the only traffic between the Master and the nodes.
- **Data-plane traffic** is customer VPN/proxy traffic, which goes **customer → node directly** and never transits the Master.

## Customer → node direct path

Customers' proxy connections terminate on the regional node's own proxy inbounds (Hysteria2 / SS / VLESS-Reality) and its own TLS for its own node domain. The Master is not in the data path.

## Master never proxies (no exception)

The Master carries **no proxy traffic — full stop.** The former §4.1 co-location exception is **retired**
([DECISIONS.md](DECISIONS.md) ADR-001): the DE node now runs on its **own dedicated VPS** (`de1`, `5.249.160.59`),
reached by customers directly like any other node. The Master is control-plane only.

## Phase 2 preflight — current network state (2026-06-15, read-only)

- **Public surface:** only **SSH:22** (`0.0.0.0` + IPv6) is listening publicly. Ports **80/443 are free** (nginx not
  installed yet). All planned Master service ports (8190/8191/8192/8197) are free.
- **Firewall: none active** — `ufw inactive`, `iptables` policies all `ACCEPT` with no rules, empty `nft` ruleset.
  In practice exposure is limited today (only SSH is bound publicly), but **any future port bound to `0.0.0.0`
  becomes internet-reachable with no filtering**. A firewall/exposure plan (B3) is a prerequisite before opening
  Hiddify proxy ports, and must guarantee SSH stays reachable. See `PHASE2_MASTER_DE_HIDDIFY_PREFLIGHT.md`.
- **Co-location TLS conflict — RESOLVED by removing co-location.** Because the DE node now lives on its **own VPS**
  ([DECISIONS.md](DECISIONS.md) ADR-001), there is **no 443 contention on the Master**: the Master nginx will own
  80/443 solely for the control-plane subdomains (`api/bot/panel/app/sub/www`), and Hiddify owns 80/443 on the
  separate DE VPS. The §B1 audit options below are now **historical** (kept for the record).

## Phase 3 audit — co-location TLS/SNI strategy (HISTORICAL — co-location retired)

> These options were evaluated while DE-on-Master was still planned. **Option C (separate DE VPS) was chosen**, so the
> 443-sharing problem no longer exists on the Master. Retained for history; see [PHASE3_HIDDIFY_AUDIT_PLAN.md](PHASE3_HIDDIFY_AUDIT_PLAN.md).

- Only **one** process can bind public **443**; with a single shared IP, sharing it would have been an **SNI/host-routing**
  problem. The shapes considered:
  - **Option A:** Master nginx fronts 443, reverse-proxying the co-located Hiddify HTTP; proxy inbounds on dedicated ports.
  - **Option B:** Hiddify HAProxy fronts 443 (SNI split) with the Master nginx behind it.
  - **Option C (CHOSEN):** **separate DE VPS** — no 443 sharing at all (§6.1 made this a code-free move).
- Customers still receive only `https://sub.unseen.click/s/<token>`; the node's raw sub URL stays internal.

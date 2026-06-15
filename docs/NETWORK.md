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

## Master never proxies (except co-located DE)

The Master carries **no proxy traffic**, with the one documented exception: the **co-located DE node** runs on the Master box (§4.1). That DE proxy traffic is budgeted and watched so it cannot starve the control plane, and the DE node is movable to its own VPS with no code change if it outgrows the shared box.

## Phase 2 preflight — current network state (2026-06-15, read-only)

- **Public surface:** only **SSH:22** (`0.0.0.0` + IPv6) is listening publicly. Ports **80/443 are free** (nginx not
  installed yet). All planned Master service ports (8190/8191/8192/8197) are free.
- **Firewall: none active** — `ufw inactive`, `iptables` policies all `ACCEPT` with no rules, empty `nft` ruleset.
  In practice exposure is limited today (only SSH is bound publicly), but **any future port bound to `0.0.0.0`
  becomes internet-reachable with no filtering**. A firewall/exposure plan (B3) is a prerequisite before opening
  Hiddify proxy ports, and must guarantee SSH stays reachable. See `PHASE2_MASTER_DE_HIDDIFY_PREFLIGHT.md`.
- **Co-location TLS conflict:** nginx (control plane) and Hiddify (DE node) both expect 80/443 — see
  [PORTS.md](PORTS.md). Unresolved until the Phase 3 audit informs the coexistence strategy.

## Phase 3 audit — co-location TLS/SNI strategy (proposed)

Full analysis in [PHASE3_HIDDIFY_AUDIT_PLAN.md](PHASE3_HIDDIFY_AUDIT_PLAN.md). Summary:

- Only **one** process can bind public **443**; with a single shared IP, sharing it is an **SNI/host-routing**
  problem, not a vhost add. Two viable shapes:
  - **Option A (recommended for co-location):** **Master nginx fronts 443**, host-routing control-plane subdomains to
    loopback services and reverse-proxying `node-de.unseen.click` panel/subscription HTTP to a **Docker Hiddify on a
    remapped port** (e.g. `127.0.0.1:8443`). Proxy inbounds (Hysteria2 UDP, SS, Reality) get **dedicated ports**.
  - **Option B:** Hiddify **HAProxy fronts 443** (SNI split) with the Master nginx behind it — native to Hiddify but
    inverts the "nginx is sole 443 owner" design and couples control-plane TLS to Hiddify (higher risk).
  - **Option C (lowest risk):** **separate DE VPS** — no 443 sharing at all (§6.1 makes this code-free).
- Customers still receive only `https://sub.unseen.click/s/<token>`; the node's raw sub URL stays internal.
- **[LIVE]** the final 443 owner and Reality's port are confirmed on a snapshot/sandbox before install is authorized.

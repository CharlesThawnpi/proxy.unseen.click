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

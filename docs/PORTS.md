# PORTS

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §5, §8
> **Status:** Phase 1 skeleton — decided from plan

Port allocation on the Master VPS. All application services bind loopback only; nginx owns the public ports.

## Loopback ports (bound to 127.0.0.1)

| Port | Service | Subdomain |
|---|---|---|
| `8197` | `unseenproxy-sidecar` (subscription delivery `/s/<token>`) | `sub.unseen.click` |
| `8190` | `unseenproxy-admin` (web admin dashboard) | `panel.unseen.click` |
| `8191` | `unseenproxy-portal` (customer self-service portal) | `app.unseen.click` |
| `8192` | `unseenproxy-api` (internal/service API layer) | `api.unseen.click` |

The bot uses long-poll (no inbound port) or webhook mode via `bot.unseen.click`.

## Public ports (owned by nginx)

| Port | Owner | Role |
|---|---|---|
| `80` | nginx | HTTP — ACME challenge / redirect to HTTPS |
| `443` | nginx | HTTPS — TLS termination, subdomain routing to loopback services |

nginx is the **sole** owner of `:80`/`:443` on the Master. Node proxy ports are managed independently on each node by Hiddify Manager (not Master concerns).

> Node-side proxy inbound ports: Verified in Phase 3 (node test gate).

### de1 node ports after fresh Hiddify reinstall (Phase 9, 2026-06-16)

On `de1` (`status=test`), Hiddify manages its own iptables (no ufw). Externally relevant: **22/tcp** (SSH, key-only),
**80/tcp** (ACME/redirect), **443/tcp** (panel/sub + TLS proxies), **443/udp** (Hysteria2/QUIC). Shadowsocks is
faketls-fronted (`8388` loopback only); MariaDB/Redis loopback only; many high-range Reality/proxy inbound ports are
Hiddify-managed. All four required ACCEPTs (22/80/443 tcp + 443 udp) present; SSH verified reachable. Real-device
reachability for QUIC/Reality is a #TASK_for_Charles. See [PHASE9_DE1_REBUILD_FRESH_HIDDIFY.md](PHASE9_DE1_REBUILD_FRESH_HIDDIFY.md).

> **Re-confirmed 2026-06-16** when the node domain `node-de.unseen.click` + cert were set: the four ACCEPTs are
> unchanged and **no firewall/port change was made**. `80/tcp` must stay open — Hiddify/acme.sh uses it for the ACME
> HTTP-01 challenge when issuing/renewing the domain cert. `443/tcp` serves the panel/subscription + TLS proxies for
> the node domain; `443/udp` serves Hysteria2/QUIC.

> **Client-side ports are NOT node ports.** A Hiddify-App import error citing `127.0.0.1:64127` (seen on de1's first
> real-device attempt) is the **App's own embedded core / clash-api local control port on the phone**, not a de1
> listener — the node emits no `64127` (the sing-box client template's clash-api is the standard `127.0.0.1:9090`).
> Don't add/open any node port for it; it's an app-side condition. See [HIDDIFY_NODE_INSTALL_RUNBOOK.md](HIDDIFY_NODE_INSTALL_RUNBOOK.md) §5B.

### de1 UNSEEN-only product ports (after 2026-06-16 prune)

After pruning de1 to the UNSEEN product set, the customer profile uses these node-de ports (no firewall change was made
— INPUT policy is ACCEPT, so all are reachable; values are non-secret ports):

| Product | Protocol | node-de port |
|---|---|---|
| FAST1 | Hysteria2 | **udp/14430** (QUIC) |
| FAST2 | Shadowsocks | **16753** (tcp+udp) |
| Secure | VLESS-Reality | **tcp/443** (decoy SNI `i.pinimg.com`) |

`hiddify-ss-faketls` (loopback `:8388`) is now **inactive** (faketls SS replaced by plain Shadowsocks for sing-box
compatibility) — expected, not a fault. `80/tcp` stays open for ACME renewal; `443/tcp`+`443/udp` remain. Port numbers
above are Hiddify-assigned and may differ per node/version — read them from the generated profile, never hardcode.

## Phase 2 preflight — current live port map (Master, 2026-06-15)

Observed via `ss -tulpn` (read-only). See `PHASE2_MASTER_DE_HIDDIFY_PREFLIGHT.md`.

| Port | Bind | Owner now | Status |
|---|---|---|---|
| 22/tcp | `0.0.0.0` + `[::]` | sshd | in use (keep) |
| 53 udp/tcp | `127.0.0.x` | systemd-resolved | loopback stub |
| 43417 / 22815 tcp | `127.0.0.1` | transient tooling (ephemeral) | not project services |
| **80, 443** | — | **FREE** | reserved for the **control-plane nginx** (no Hiddify contention — co-location retired) |
| 8190 / 8191 / 8192 / 8197 | — | **FREE** | reserved for admin/portal/api/sidecar |

**Co-location port conflict — RESOLVED (historical).** The original worry was that a co-located Hiddify would fight
the control-plane nginx for **80/443**. With the DE node moved to its **own VPS** ([DECISIONS.md](DECISIONS.md)
ADR-001), the Master nginx owns 80/443 **solely** for `api/bot/panel/app/sub/www`, and Hiddify owns 80/443 on the
separate DE VPS (`5.249.160.59`). No shared-443 problem remains on the Master.

## Phase 3 audit — Hiddify port behavior (tiered)

See [PHASE3_HIDDIFY_AUDIT_PLAN.md](PHASE3_HIDDIFY_AUDIT_PLAN.md) for sources.

- **[VERIFIED]** Standard install runs its **own nginx + HAProxy** and **takes 80/443**. **Docker install** binds
  `80:80`/`443:443` **by default but can be remapped** (e.g. `8443`) to run **behind an existing nginx** — the B1 path.
- **[VERIFIED]** Panel + subscription are served over **443** (HTTP/TLS) on a **secret proxy path**.
- **[LIVE/ASSUMPTION]** Protocol inbound ports are **panel-assigned/configurable** — typical: VLESS-Reality on 443/TCP
  (SNI stealth), Hysteria2 on a high **UDP** port, Shadowsocks on its own port. **Exact numbers must be read from
  `ss -tulpn` post-install; do NOT hardcode.**
- **Key constraint:** Hysteria2 (UDP/QUIC), Reality (raw-TLS/SNI), and SS are **not HTTP** and **cannot be nginx
  HTTP-reverse-proxied** — they need dedicated ports or HAProxy SNI fronting. Only the panel/subscription HTTP(S)
  can sit behind the Master nginx.
- **[DE node `de1`, Hiddify v12.3.3 installed 2026-06-16]** Now listening: **443 tcp+udp** (panel/sub + Hysteria2/QUIC),
  **8388** Shadowsocks, plus many Reality/other proxy inbound ports (tcp+udp); `3306`/`6379` loopback only; **SSH `22`**
  public. **ufw active but explicitly allows only 22/tcp** — Hiddify manages the proxy ports via its own iptables;
  ⚠ confirm proxy-port external reachability (ufw default-deny vs Hiddify's ACCEPT rules). See
  [PHASE3_DE1_HIDDIFY_LIVE_VERIFY.md](PHASE3_DE1_HIDDIFY_LIVE_VERIFY.md).
- **[Reachability from Master, 2026-06-16]** tcp **22/80/443 OPEN** externally (443 TLS → 200, panel/Reality front);
  **8388 (Shadowsocks) FILTERED** externally; UDP (Hysteria2 443/udp) not TCP-probeable → real-device test needed.
  ufw added 4 Hiddify proxy ACCEPT rules but not all inbounds are open — **node-tuning before live**: ensure each
  served protocol's port is allowed (and confirm SS's actual public port).
- **[LIVE 2026-06-15]** A test Docker install (v12.3.3) briefly bound host **80 + 443 via `docker-proxy`** (bridge
  mode; redis/mariadb stayed container-internal), then was **torn down — 80/443 are FREE again**. Because the DE node
  now moves to a **separate VPS**, the §B1 80/443 co-location conflict on the Master no longer applies; the Master
  nginx (when built) will own 80/443 with no Hiddify contention. See `PHASE3_HIDDIFY_LIVE_VERIFY.md`.

## de1 firewall verified (Phase 4 pre-live tuning, 2026-06-16)

ufw + Hiddify share one **nf_tables** ruleset; Hiddify's `ACCEPT` rules sit **ahead of ufw's chains** in `INPUT`, so
required ports are accepted before ufw's default-deny. **No firewall change was required.** Verified externally from
the Master (TCP connect only, no payloads): **22/80/443 tcp OPEN** (443 TLS→HTTP 200), **55573 tcp OPEN**, 443 udp +
dynamic Hiddify inbounds accepted (Hysteria2/QUIC — real-device test needed). **8388 is filtered by design**
(`ss-server` binds loopback only; Shadowsocks reaches clients via HAProxy/faketls over 443 — do **not** open raw 8388).
3306/6379 loopback-only. Note: dynamic proxy ports are regenerated on rebuild — don't hardcode them. See
[PHASE4_PRELIVE_DE1_TUNING.md](PHASE4_PRELIVE_DE1_TUNING.md).

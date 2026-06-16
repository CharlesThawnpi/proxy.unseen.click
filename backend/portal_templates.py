"""HTML templates for the dry-run customer portal.

The renderer is intentionally tiny and stdlib-only. Every dynamic value goes through `html.escape`;
template helpers return strings assembled from escaped parts only.
"""
from __future__ import annotations

from html import escape

from .portal_static import PORTAL_CSS
from . import portal_viewmodels as vm


def h(value) -> str:
    return escape("" if value is None else str(value), quote=True)


def badge(label: str, tone: str = "neutral") -> str:
    safe_tone = tone if tone in {"ok", "warn", "bad", "info", "neutral"} else "neutral"
    return f'<span class="badge {safe_tone}">{h(label)}</span>'


def layout(title: str, body: str, current: str = "") -> str:
    nav = [
        ("/", "Home", "home"),
        ("/plans", "Plans", "plans"),
        ("/customer/status", "Status", "status"),
        ("/help", "Help", "help"),
    ]
    nav_html = "".join(
        f'<a href="{h(path)}"{" aria-current=\"page\"" if key == current else ""}>{h(label)}</a>'
        for path, label, key in nav
    )
    return f"""<!doctype html>
<html lang="my">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{h(title)} - UNSEEN PROXY</title>
  <style>{PORTAL_CSS}</style>
</head>
<body>
  <header class="topbar">
    <div class="brand">UNSEEN PROXY</div>
    <nav class="nav" aria-label="Portal navigation">{nav_html}</nav>
  </header>
  <main class="shell">{body}</main>
</body>
</html>"""


def page_head(title: str, lead: str, extra: str = "") -> str:
    return f"""<div class="page-head">
  <div>
    <h1>{h(title)}</h1>
    <p class="lead">{h(lead)}</p>
  </div>
  {extra}
</div>"""


def render_home() -> str:
    body = page_head(
        "Portal foundation",
        "Customer status, Plan ကြည့်ရန် နှင့် subscription landing အတွက် dry-run preview ဖြစ်သည်။",
    )
    body += """<section class="grid three">
  <article class="card"><h2>Status</h2><p class="muted">Public customer code ဖြင့် subscription အခြေအနေကို ကြည့်ရန်။</p></article>
  <article class="card"><h2>Plans</h2><p class="muted">DB ထဲရှိ Trial, Basic, Core, Plus, Pro, Max rules ကို ပြသသည်။</p></article>
  <article class="card"><h2>Subscription link</h2><p class="muted">Branded link placeholder သာ ပြသပြီး raw proxy link မပြပါ။</p></article>
</section>"""
    return layout("Portal", body, "home")


def render_plans(plans: list[dict]) -> str:
    rows = []
    for plan in plans:
        region_bits = []
        for region in plan["regions"]:
            label = f'{region["code"]} {region["name"]}'
            if region["premium_only"]:
                label += " Premium"
            region_bits.append(
                f'{badge(label, "neutral")} {badge(region["availability"]["label"], region["availability"]["tone"])}'
            )
        proto_bits = [badge(p["label"], "info" if p["label"].startswith("Fast") else "neutral")
                      for p in plan["protocols"]]
        trial = badge("Trial", "info") if plan["is_trial"] else ""
        rows.append(f"""<tr>
  <td><strong>{h(plan["name"])}</strong><div class="meta">{h(plan["plan_code"])} {trial}</div></td>
  <td>{h(plan["data_limit"])}</td>
  <td>{h(plan["duration"])}</td>
  <td class="price">{h(plan["price"])}</td>
  <td>{h(plan["devices"])}</td>
  <td><div class="pillset">{''.join(region_bits)}</div></td>
  <td><div class="pillset">{''.join(proto_bits)}</div></td>
</tr>""")
    body = page_head("Plans", "Plan data, regions, protocols နှင့် availability ကို DB မှ ဖတ်ပြသည်။")
    body += f"""<section class="table-wrap" aria-label="Plan table">
  <table>
    <thead><tr><th>Plan</th><th>Data</th><th>Duration</th><th>Price</th><th>Devices</th><th>Regions</th><th>Fast / Secure</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
</section>"""
    return layout("Plans", body, "plans")


def render_dashboard(data: dict) -> str:
    stat_cards = f"""<section class="grid three">
  <div class="kpi"><span class="meta">Customer</span><span class="value">{h(data["public_customer_code"])}</span></div>
  <div class="kpi"><span class="meta">Subscriptions</span><span class="value">{h(data["subscription_count"])}</span></div>
  <div class="kpi"><span class="meta">Active</span><span class="value">{h(data["active_count"])}</span></div>
</section>"""
    subs = []
    for sub in data["subscriptions"]:
        subs.append(f"""<li class="row">
  <div class="row-main"><strong>{h(sub["plan_name"])}</strong><div class="meta">{h(sub["code"])} - {h(sub["data_limit"])} - expires {h(sub["expiry_date"])}</div></div>
  <div class="pillset">{badge(sub["status"]["label"], sub["status"]["tone"])}<a class="button" href="/subscriptions/{h(sub["id"])}">View</a></div>
</li>""")
    sub_html = "".join(subs) if subs else '<li class="row"><span class="muted">Subscription မရှိသေးပါ။</span></li>'
    body = page_head("Customer status", "Public customer code ကိုသာ primary identity အဖြစ် ပြသသည်။")
    body += stat_cards
    body += f"""<section class="panel" style="margin-top:8px">
  <h2>Subscriptions</h2>
  <ul class="compact-list">{sub_html}</ul>
</section>"""
    return layout("Customer status", body, "status")


def render_subscription(data: dict) -> str:
    delivery_modes = "".join(
        f'<span>{h(mode["label"])} {badge(mode["badge"]["label"], mode["badge"]["tone"])}</span>'
        for mode in data["delivery"]["modes"]
    )
    regions = []
    for region in data["regions"]:
        proto = "".join(badge(p["label"], p["badge"]["tone"]) for p in region["protocols"])
        regions.append(f"""<li class="row">
  <div class="row-main"><strong>{h(region["code"])} {h(region["name"])}</strong><div class="meta">{proto}</div></div>
  {badge(region["availability"]["label"], region["availability"]["tone"])}
</li>""")
    body = page_head(
        f"Subscription {data['code']}",
        "Snapshot values နှင့် dry-run availability ကို customer-safe view ဖြင့် ပြသည်။",
        badge(data["status"]["label"], data["status"]["tone"]),
    )
    body += f"""<section class="grid two">
  <article class="panel">
    <h2>Snapshot</h2>
    <ul class="compact-list">
      <li class="row"><span>Customer</span><strong>{h(data["public_customer_code"])}</strong></li>
      <li class="row"><span>Plan</span><strong>{h(data["plan_name"])}</strong></li>
      <li class="row"><span>Data</span><strong>{h(data["data_limit"])}</strong></li>
      <li class="row"><span>Duration</span><strong>{h(data["duration"])}</strong></li>
      <li class="row"><span>Price</span><strong>{h(data["price"])}</strong></li>
      <li class="row"><span>Start</span><strong>{h(data["start_date"])}</strong></li>
      <li class="row"><span>Expiry</span><strong>{h(data["expiry_date"])}</strong></li>
      <li class="row"><span>Provision</span>{badge(data["provision_status"]["label"], data["provision_status"]["tone"])}</li>
    </ul>
  </article>
  <article class="panel">
    <h2>Branded link</h2>
    <code class="link-placeholder">{h(data["delivery"]["placeholder"])}</code>
    <div class="actions">{delivery_modes}</div>
    <p class="meta">Placeholder only. Raw subscription/proxy links are not rendered.</p>
  </article>
</section>
<section class="panel" style="margin-top:8px">
  <h2>Availability</h2>
  <ul class="compact-list">{''.join(regions)}</ul>
</section>"""
    return layout("Subscription", body, "status")


def render_branded_placeholder() -> str:
    body = page_head(
        "Subscription landing",
        "ဤ route shape သည် /s/<opaque-token> အတွက် placeholder သာဖြစ်ပြီး token resolution မလုပ်ပါ။",
        badge("Placeholder", "info"),
    )
    body += """<section class="panel">
  <h2>Delivery status</h2>
  <p class="muted">Future portal auth နှင့် live subscription resolution မရှိသေးသောကြောင့် link payload မပြပါ။</p>
  <div class="pillset">""" + badge("Deep-link planned", "neutral") + badge("Copy-link planned", "neutral") + badge("QR planned", "neutral") + """</div>
</section>"""
    return layout("Subscription landing", body, "status")


def render_help() -> str:
    body = page_head("Help", "Support handoff အတွက် customer-safe information သာ ပြထားသည်။")
    body += """<section class="grid two">
  <article class="panel"><h2>Plan ပြောင်းရန်</h2><p class="muted">လက်ရှိ subscription status ကို screenshot မလိုဘဲ public customer code ဖြင့် support ကို ပြောနိုင်သည်။</p></article>
  <article class="panel"><h2>Connection issue</h2><p class="muted">Region availability ကို portal တွင် ကြည့်နိုင်သည်။ Node hostnames သို့မဟုတ် operational details မပြပါ။</p></article>
</section>"""
    return layout("Help", body, "help")


def render_state_page(kind: str) -> str:
    titles = {
        "unavailable": ("Unavailable", "ယာယီမရနိုင်ပါ။ နောက်မှ ထပ်စမ်းကြည့်ပါ။", "warn"),
        "expired": ("Expired", "Subscription သက်တမ်းကုန်နေသည်။ Renew flow ကို နောက်ပိုင်းတွင် ချိတ်ဆက်မည်။", "bad"),
        "not-found": ("Not found", "ရှာမတွေ့ပါ။ Link သို့မဟုတ် status request ကို စစ်ဆေးပါ။", "neutral"),
    }
    title, lead, tone = titles.get(kind, titles["not-found"])
    body = page_head(title, lead, badge(title, tone))
    body += '<section class="panel"><p class="muted">No private platform IDs, raw links, or operational endpoints are shown.</p></section>'
    return layout(title, body, "")


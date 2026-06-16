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
        "Customer Portal",
        "Plan, subscription status နှင့် support အချက်အလက်များကို တစ်နေရာတည်းမှာ ကြည့်ရန် preview ဖြစ်သည်။",
    )
    body += """<section class="grid three" aria-label="Portal summary">
  <article class="card"><h2>Status</h2><p class="muted">Public customer code ဖြင့် subscription အခြေအနေကို ချက်ချင်းစစ်နိုင်သည်။</p></article>
  <article class="card"><h2>Plans</h2><p class="muted">Trial, Basic, Core, Plus, Pro, Max ကို DB data အတိုင်း ပြသည်။</p></article>
  <article class="card"><h2>Subscription link</h2><p class="muted">Branded placeholder သာ ပြပြီး raw proxy link မပြပါ။</p></article>
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
  <td data-label="Plan"><strong>{h(plan["name"])}</strong><div class="meta">{h(plan["plan_code"])} {trial}</div></td>
  <td data-label="Data">{h(plan["data_limit"])}</td>
  <td data-label="Days">{h(plan["duration"])}</td>
  <td data-label="Price" class="price">{h(plan["price"])}</td>
  <td data-label="Devices">{h(plan["devices"])}</td>
  <td data-label="Regions"><div class="pillset">{''.join(region_bits)}</div></td>
  <td data-label="Protocols"><div class="pillset">{''.join(proto_bits)}</div></td>
</tr>""")
    body = page_head("Plans", "Plan data, region availability နှင့် Fast/Secure options ကို DB မှ ဖတ်ပြသည်။")
    body += f"""<section class="table-wrap" aria-label="Plan table">
  <table>
    <thead><tr><th>Plan</th><th>Data</th><th>Duration</th><th>Price</th><th>Devices</th><th>Regions</th><th>Fast / Secure</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
</section>"""
    return layout("Plans", body, "plans")


def render_dashboard(data: dict) -> str:
    stat_cards = f"""<section class="grid three" aria-label="Customer summary">
  <div class="kpi"><span class="meta">Customer code</span><span class="value">{h(data["public_customer_code"])}</span></div>
  <div class="kpi"><span class="meta">Subscriptions</span><span class="value">{h(data["subscription_count"])}</span></div>
  <div class="kpi"><span class="meta">Active</span><span class="value">{h(data["active_count"])}</span></div>
</section>"""
    subs = []
    for sub in data["subscriptions"]:
        subs.append(f"""<li class="row">
  <div class="row-main"><strong>{h(sub["plan_name"])}</strong><div class="meta">{h(sub["code"])} - {h(sub["data_limit"])} - expires {h(sub["expiry_date"])} MMT</div></div>
  <div class="pillset">{badge(sub["status"]["label"], sub["status"]["tone"])}<a class="button" href="/subscriptions/{h(sub["id"])}">ကြည့်ရန်</a></div>
</li>""")
    sub_html = "".join(subs) if subs else '<li class="row"><span class="muted">Subscription မရှိသေးပါ။</span></li>'
    body = page_head("Customer status", "Public customer code ကိုသာ identity အဖြစ် ပြထားသည်။")
    body += stat_cards
    body += f"""<section class="panel stack-sm">
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
        "Plan snapshot, delivery placeholder နှင့် region status ကို customer-safe view ဖြင့် ပြသည်။",
        badge(data["status"]["label"], data["status"]["tone"]),
    )
    body += f"""<section class="status-strip" aria-label="Subscription quick status">
  <div class="kpi"><span class="meta">Plan</span><span class="value">{h(data["plan_name"])}</span></div>
  <div class="kpi"><span class="meta">Data</span><span class="value">{h(data["data_limit"])}</span></div>
  <div class="kpi"><span class="meta">Expiry (MMT)</span><span class="value">{h(data["expiry_date"])}</span></div>
  <div class="kpi"><span class="meta">Provision</span><span class="value">{h(data["provision_status"]["label"])}</span></div>
</section>
<section class="grid two">
  <article class="panel">
    <h2>Snapshot</h2>
    <ul class="compact-list">
      <li class="row"><span>Customer</span><strong>{h(data["public_customer_code"])}</strong></li>
      <li class="row"><span>Plan</span><strong>{h(data["plan_name"])}</strong></li>
      <li class="row"><span>Data</span><strong>{h(data["data_limit"])}</strong></li>
      <li class="row"><span>Duration</span><strong>{h(data["duration"])}</strong></li>
      <li class="row"><span>Price</span><strong>{h(data["price"])}</strong></li>
      <li class="row"><span>Start (MMT)</span><strong>{h(data["start_date"])}</strong></li>
      <li class="row"><span>Expiry (MMT)</span><strong>{h(data["expiry_date"])}</strong></li>
      <li class="row"><span>Provision</span>{badge(data["provision_status"]["label"], data["provision_status"]["tone"])}</li>
    </ul>
  </article>
  <article class="panel">
    <h2>Branded link</h2>
    <code class="link-placeholder">{h(data["delivery"]["placeholder"])}</code>
    <div class="actions">{delivery_modes}</div>
    <p class="section-note">Placeholder only. Raw subscription/proxy links are not rendered.</p>
  </article>
</section>
<section class="panel stack-sm">
  <h2>Availability</h2>
  <p class="section-note">Region status သာ ပြထားသည်။ Node hostname/IP မပြပါ။</p>
  <ul class="compact-list">{''.join(regions)}</ul>
</section>"""
    return layout("Subscription", body, "status")


def render_branded_placeholder() -> str:
    body = page_head(
        "Subscription landing",
        "ဤ /s/<opaque-token> route သည် placeholder သာဖြစ်ပြီး token resolution မလုပ်ပါ။",
        badge("Placeholder", "info"),
    )
    body += """<section class="panel stack-sm">
  <h2>Delivery status</h2>
  <p class="muted">Portal auth နှင့် live subscription resolution မရှိသေးသောကြောင့် link payload မပြပါ။</p>
  <div class="pillset">""" + badge("Deep-link planned", "neutral") + badge("Copy-link planned", "neutral") + badge("QR planned", "neutral") + """</div>
</section>"""
    return layout("Subscription landing", body, "status")


def render_branded_resolved(data: dict) -> str:
    body = page_head(
        "Subscription ready",
        "Token ကို စစ်ပြီးပါပြီ။ Session helper ကို dry-run အနေဖြင့် ပြင်ဆင်ထားသည်။",
        badge("Verified", "ok"),
    )
    body += f"""<section class="panel stack-sm">
  <h2>Safe access</h2>
  <ul class="compact-list">
    <li class="row"><span>Customer</span><strong>{h(data["public_customer_code"])}</strong></li>
    <li class="row"><span>Subscription</span><strong>{h(data["subscription_code"])}</strong></li>
    <li class="row"><span>Session</span>{badge("Dry-run session prepared", "info")}</li>
  </ul>
  <p class="section-note">No raw token or session id is rendered. Cookie setting is future work.</p>
</section>"""
    return layout("Subscription ready", body, "status")


def render_help() -> str:
    body = page_head("Help", "Support အတွက် customer-safe information သာ ပြထားသည်။")
    body += """<section class="grid two">
  <article class="panel"><h2>Plan ပြောင်းရန်</h2><p class="muted">Public customer code နှင့် လက်ရှိ Plan ကို support သို့ ပြောနိုင်သည်။</p></article>
  <article class="panel"><h2>Connection issue</h2><p class="muted">Region availability ကို ကြည့်နိုင်သည်။ Node hostname/IP မပြပါ။</p></article>
</section>"""
    return layout("Help", body, "help")


def render_auth_required() -> str:
    body = page_head(
        "Session required",
        "Dashboard နှင့် subscription details ကြည့်ရန် valid portal session လိုအပ်သည်။",
        badge("Auth required", "warn"),
    )
    body += """<section class="panel">
  <p class="muted">Public pages ဖြစ်သော Home, Plans, Help ကိုတော့ session မလိုဘဲ ကြည့်နိုင်သည်။</p>
</section>"""
    return layout("Session required", body, "")


def render_state_page(kind: str) -> str:
    titles = {
        "unavailable": ("Unavailable", "ယာယီမရနိုင်ပါ။ နောက်မှ ထပ်စမ်းကြည့်ပါ။", "warn"),
        "degraded": ("Degraded", "Service အကန့်အသတ်ရှိနိုင်သည်။ ရနိုင်သော Region ကို ရွေးပါ။", "warn"),
        "expired": ("Expired", "Subscription သက်တမ်းကုန်နေသည်။ Renew flow ကို နောက်ပိုင်းတွင် ချိတ်ဆက်မည်။", "bad"),
        "not-found": ("Not found", "ရှာမတွေ့ပါ။ Link သို့မဟုတ် status request ကို စစ်ဆေးပါ။", "neutral"),
    }
    title, lead, tone = titles.get(kind, titles["not-found"])
    body = page_head(title, lead, badge(title, tone))
    body += '<section class="panel"><p class="muted">No private platform IDs, raw links, or operational endpoints are shown.</p></section>'
    return layout(title, body, "")

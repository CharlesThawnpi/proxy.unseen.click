"""Static assets for the render-only customer portal foundation.

No external fonts, images, scripts, or CDN dependencies are used. The CSS is embedded by
the template renderer so dry-run CLI output is self-contained and never needs a web server.
"""
from __future__ import annotations


PORTAL_CSS = """
:root {
  color-scheme: light;
  --bg: #f6f8fa;
  --panel: #ffffff;
  --panel-muted: #f0f3f6;
  --border: #d0d7de;
  --border-strong: #8c959f;
  --text: #24292f;
  --muted: #57606a;
  --link: #0969da;
  --ok-bg: #dafbe1;
  --ok-text: #116329;
  --warn-bg: #fff8c5;
  --warn-text: #7d4e00;
  --bad-bg: #ffebe9;
  --bad-text: #a40e26;
  --info-bg: #ddf4ff;
  --info-text: #0550ae;
  --shadow: 0 1px 0 rgba(27,31,36,.04);
}

* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font: 14px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
a { color: var(--link); text-decoration: none; }
a:hover, a:focus { text-decoration: underline; }
a:focus-visible, button:focus-visible { outline: 2px solid var(--link); outline-offset: 2px; }

.topbar {
  display: flex;
  gap: 10px;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  background: #24292f;
  color: #ffffff;
  border-bottom: 1px solid #1b1f24;
}
.brand { font-weight: 700; letter-spacing: 0; white-space: nowrap; }
.nav { display: flex; gap: 4px; flex-wrap: wrap; justify-content: flex-end; }
.nav a {
  color: #ffffff;
  border: 1px solid rgba(255,255,255,.18);
  border-radius: 6px;
  padding: 5px 8px;
  min-height: 30px;
}
.nav a[aria-current="page"] { background: rgba(255,255,255,.12); }

.shell {
  width: min(1180px, 100%);
  margin: 0 auto;
  padding: 10px;
}
.page-head {
  display: grid;
  grid-template-columns: 1fr;
  gap: 4px;
  margin: 4px 0 10px;
}
h1, h2, h3, p { margin-top: 0; }
h1 { font-size: 22px; line-height: 1.25; margin-bottom: 2px; }
h2 { font-size: 16px; line-height: 1.3; margin-bottom: 8px; }
h3 { font-size: 14px; line-height: 1.25; margin-bottom: 6px; }
.lead, .muted { color: var(--muted); }
.lead { margin-bottom: 0; }
.grid { display: grid; grid-template-columns: 1fr; gap: 8px; }
.grid.two, .grid.three { grid-template-columns: 1fr; }

.panel, .card {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 6px;
  box-shadow: var(--shadow);
}
.panel { padding: 10px; }
.card { padding: 9px; }
.compact-list { display: grid; gap: 6px; margin: 0; padding: 0; list-style: none; }
.row {
  display: flex;
  gap: 8px;
  align-items: center;
  justify-content: space-between;
  min-width: 0;
  padding: 7px 0;
  border-top: 1px solid var(--border);
}
.row:first-child { border-top: 0; padding-top: 0; }
.row-main { min-width: 0; }
.row-main strong, .truncate { overflow-wrap: anywhere; }
.meta { color: var(--muted); font-size: 12px; }
.kpi {
  display: grid;
  gap: 2px;
  padding: 8px;
  background: var(--panel-muted);
  border: 1px solid var(--border);
  border-radius: 6px;
}
.kpi .value { font-weight: 700; font-size: 15px; }

.badge {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  padding: 2px 7px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  border: 1px solid transparent;
  white-space: nowrap;
}
.badge.ok { color: var(--ok-text); background: var(--ok-bg); border-color: #aceebb; }
.badge.warn { color: var(--warn-text); background: var(--warn-bg); border-color: #f0d98c; }
.badge.bad { color: var(--bad-text); background: var(--bad-bg); border-color: #ffb4ab; }
.badge.info { color: var(--info-text); background: var(--info-bg); border-color: #80ccff; }
.badge.neutral { color: var(--muted); background: var(--panel-muted); border-color: var(--border); }

.table-wrap { overflow-x: auto; border: 1px solid var(--border); border-radius: 6px; }
table { width: 100%; border-collapse: collapse; background: var(--panel); min-width: 720px; }
th, td { padding: 7px 8px; border-top: 1px solid var(--border); text-align: left; vertical-align: top; }
thead th { border-top: 0; background: var(--panel-muted); font-size: 12px; color: var(--muted); }
.price { font-weight: 700; white-space: nowrap; }
.pillset { display: flex; flex-wrap: wrap; gap: 4px; }
.link-placeholder {
  display: block;
  width: 100%;
  padding: 8px;
  border: 1px dashed var(--border-strong);
  border-radius: 6px;
  background: var(--panel-muted);
  color: var(--text);
  overflow-wrap: anywhere;
}
.actions { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 30px;
  padding: 5px 9px;
  border: 1px solid var(--border-strong);
  border-radius: 6px;
  background: var(--panel);
  color: var(--text);
  font-weight: 600;
}

@media (min-width: 760px) {
  .topbar { padding: 10px 18px; }
  .shell { padding: 14px 16px; }
  .page-head { grid-template-columns: 1fr auto; align-items: end; }
  .grid.two { grid-template-columns: minmax(0, 1.25fr) minmax(280px, .75fr); }
  .grid.three { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  h1 { font-size: 24px; }
}

@media (max-width: 480px) {
  body { font-size: 13px; }
  .topbar { align-items: flex-start; flex-direction: column; }
  .nav { justify-content: flex-start; }
  .row { align-items: flex-start; flex-direction: column; gap: 4px; }
  .badge { white-space: normal; }
}
"""


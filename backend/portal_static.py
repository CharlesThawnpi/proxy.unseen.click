"""Static assets for the render-only customer portal foundation.

No external fonts, images, scripts, or CDN dependencies are used. The CSS is embedded by
the template renderer so dry-run CLI output is self-contained and never needs a web server.
"""
from __future__ import annotations


PORTAL_CSS = """
:root {
  color-scheme: light;
  --bg: #f5f7f9;
  --panel: #ffffff;
  --panel-muted: #eef2f6;
  --border: #c9d1d9;
  --border-strong: #7d8590;
  --text: #20252b;
  --muted: #59636e;
  --link: #0967c2;
  --ok-bg: #daf5df;
  --ok-text: #145c2a;
  --warn-bg: #fff3c4;
  --warn-text: #6f4a00;
  --bad-bg: #ffebe9;
  --bad-text: #9d1828;
  --info-bg: #ddf1ff;
  --info-text: #0b5394;
  --shadow: 0 1px 0 rgba(27,31,36,.04);
}

* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font: 13px/1.42 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
a { color: var(--link); text-decoration: none; }
a:hover, a:focus { text-decoration: underline; }
a:focus-visible, button:focus-visible { outline: 2px solid var(--link); outline-offset: 2px; }

.topbar {
  display: flex;
  gap: 8px;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  background: #252b32;
  color: #ffffff;
  border-bottom: 1px solid #1c2228;
}
.brand { font-weight: 700; letter-spacing: 0; white-space: nowrap; }
.nav { display: flex; gap: 4px; flex-wrap: wrap; justify-content: flex-end; }
.nav a {
  color: #ffffff;
  border: 1px solid rgba(255,255,255,.18);
  border-radius: 5px;
  padding: 4px 7px;
  min-height: 28px;
}
.nav a[aria-current="page"] { background: rgba(255,255,255,.12); }

.shell {
  width: min(1180px, 100%);
  margin: 0 auto;
  padding: 8px;
}
.page-head {
  display: grid;
  grid-template-columns: 1fr;
  gap: 3px;
  margin: 2px 0 8px;
}
h1, h2, h3, p { margin-top: 0; }
h1 { font-size: 20px; line-height: 1.25; margin-bottom: 1px; }
h2 { font-size: 15px; line-height: 1.3; margin-bottom: 6px; }
h3 { font-size: 14px; line-height: 1.25; margin-bottom: 6px; }
.lead, .muted { color: var(--muted); }
.lead { margin-bottom: 0; }
.grid { display: grid; grid-template-columns: 1fr; gap: 7px; }
.grid.two, .grid.three { grid-template-columns: 1fr; }
.stack { display: grid; gap: 7px; }
.stack-sm { display: grid; gap: 5px; }
.shell > section + section { margin-top: 7px; }

.panel, .card {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 5px;
  box-shadow: var(--shadow);
}
.panel { padding: 8px; }
.card { padding: 8px; }
.compact-list { display: grid; gap: 4px; margin: 0; padding: 0; list-style: none; }
.row {
  display: flex;
  gap: 7px;
  align-items: center;
  justify-content: space-between;
  min-width: 0;
  padding: 6px 0;
  border-top: 1px solid var(--border);
}
.row:first-child { border-top: 0; padding-top: 0; }
.row-main { min-width: 0; }
.row-main strong, .truncate { overflow-wrap: anywhere; }
.meta { color: var(--muted); font-size: 12px; }
.section-note { margin: 0 0 6px; color: var(--muted); font-size: 12px; }
.kpi {
  display: grid;
  gap: 1px;
  padding: 7px;
  background: var(--panel-muted);
  border: 1px solid var(--border);
  border-radius: 5px;
}
.kpi .value { font-weight: 700; font-size: 15px; }
.status-strip {
  display: grid;
  grid-template-columns: 1fr;
  gap: 5px;
}

.badge {
  display: inline-flex;
  align-items: center;
  min-height: 20px;
  padding: 1px 6px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  border: 1px solid transparent;
  white-space: nowrap;
}
.badge.ok { color: var(--ok-text); background: var(--ok-bg); border-color: #aceebb; }
.badge.warn { color: var(--warn-text); background: var(--warn-bg); border-color: #f0d98c; }
.badge.bad { color: var(--bad-text); background: var(--bad-bg); border-color: #ffb4ab; }
.badge.info { color: var(--info-text); background: var(--info-bg); border-color: #80ccff; }
.badge.neutral { color: var(--muted); background: var(--panel-muted); border-color: var(--border); }

.table-wrap { overflow-x: auto; border: 1px solid var(--border); border-radius: 5px; }
table { width: 100%; border-collapse: collapse; background: var(--panel); min-width: 720px; }
th, td { padding: 6px 7px; border-top: 1px solid var(--border); text-align: left; vertical-align: top; }
thead th { border-top: 0; background: var(--panel-muted); font-size: 12px; color: var(--muted); }
.price { font-weight: 700; white-space: nowrap; }
.pillset { display: flex; flex-wrap: wrap; gap: 4px; }
.link-placeholder {
  display: block;
  width: 100%;
  padding: 7px;
  border: 1px dashed var(--border-strong);
  border-radius: 5px;
  background: var(--panel-muted);
  color: var(--text);
  overflow-wrap: anywhere;
}
.actions { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 7px; }
.button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 28px;
  padding: 4px 8px;
  border: 1px solid var(--border-strong);
  border-radius: 5px;
  background: var(--panel);
  color: var(--text);
  font-weight: 600;
}

@media (min-width: 760px) {
  .topbar { padding: 8px 16px; }
  .shell { padding: 10px 12px; }
  .page-head { grid-template-columns: 1fr auto; align-items: end; }
  .grid.two { grid-template-columns: minmax(0, 1.25fr) minmax(280px, .75fr); }
  .grid.three { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .status-strip { grid-template-columns: repeat(4, minmax(0, 1fr)); }
  h1 { font-size: 22px; }
}

@media (max-width: 720px) {
  .table-wrap { overflow-x: visible; border: 0; }
  table, thead, tbody, tr, th, td { display: block; min-width: 0; width: 100%; }
  thead { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
  tr {
    margin-bottom: 7px;
    border: 1px solid var(--border);
    border-radius: 5px;
    background: var(--panel);
    box-shadow: var(--shadow);
  }
  td {
    display: grid;
    grid-template-columns: 86px minmax(0, 1fr);
    gap: 6px;
    align-items: start;
    border-top: 1px solid var(--border);
  }
  td:first-child { border-top: 0; }
  td::before {
    content: attr(data-label);
    color: var(--muted);
    font-size: 11px;
    font-weight: 600;
  }
}

@media (max-width: 480px) {
  body { font-size: 13px; overflow-x: hidden; }
  .topbar { align-items: flex-start; flex-direction: column; }
  .nav { justify-content: flex-start; }
  .row { align-items: flex-start; flex-direction: column; gap: 4px; }
  .badge { white-space: normal; }
  .shell { padding: 7px; }
}
"""

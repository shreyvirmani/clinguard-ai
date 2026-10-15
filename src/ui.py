"""Presentation helpers for the Streamlit dashboard: the dark-navy / teal theme and small HTML components.

Everything is self-contained: inline SVG, system fonts, no external images, fonts or scripts.
"""

from __future__ import annotations

import html as _html
from typing import Any, Iterable, Sequence

from .constants import APP_NAME, APP_SUBTITLE, DISCLAIMER_SHORT, EVALUATION_MODE

STATUS_CLASS = {"PASS": "pass", "FAIL": "fail", "NEEDS_REVIEW": "review"}
STATUS_TEXT = {"PASS": "PASS", "FAIL": "FAIL", "NEEDS_REVIEW": "NEEDS REVIEW"}
STATUS_ICON = {"PASS": "&#10003;", "FAIL": "&#10005;", "NEEDS_REVIEW": "&#9888;"}

CSS = """
<style>
:root{
  --bg0:#050a16; --bg1:#0a1224; --card:#0d1930; --card2:#122244; --line:rgba(148,163,184,.15);
  --teal:#2dd4bf; --teal2:#14b8a6; --tx:#e6edf7; --mut:#8da2bf;
  --pass:#34d399; --fail:#f87171; --rev:#fbbf24;
  --font: Inter, "Segoe UI", system-ui, -apple-system, Roboto, "Helvetica Neue", Arial, sans-serif;
}
html, body, .stApp, [data-testid="stAppViewContainer"]{
  background:
    radial-gradient(1100px 560px at 88% -8%, rgba(45,212,191,.11), transparent 60%),
    radial-gradient(900px 520px at -8% 6%, rgba(59,130,246,.09), transparent 55%),
    linear-gradient(180deg,#050a16 0%,#0a1224 100%) !important;
  color:var(--tx);
}
[data-testid="stHeader"]{background:transparent;}
#MainMenu, footer{visibility:hidden;}
.block-container{padding-top:1.4rem;padding-bottom:4rem;max-width:1280px;}
section[data-testid="stSidebar"]{
  background:linear-gradient(180deg,#06101f 0%,#0a1428 100%) !important;
  border-right:1px solid var(--line);
}
section[data-testid="stSidebar"] .block-container{padding-top:1.2rem;}

/* ---------- hero ---------- */
.cg-hero{
  display:flex;align-items:center;gap:1.2rem;padding:1.4rem 1.6rem;border-radius:20px;
  background:
    linear-gradient(135deg,rgba(45,212,191,.12),rgba(15,27,51,.2) 45%),
    linear-gradient(180deg,var(--card2),var(--card));
  border:1px solid rgba(45,212,191,.25);box-shadow:0 18px 50px rgba(0,0,0,.35), inset 0 1px 0 rgba(255,255,255,.04);
  font-family:var(--font);
}
.cg-logo{flex:0 0 auto;filter:drop-shadow(0 6px 18px rgba(45,212,191,.35));}
.cg-title{margin:0;font-size:2.35rem;font-weight:800;letter-spacing:-.025em;line-height:1.1;
  background:linear-gradient(90deg,#f1f5f9 0%,#5eead4 70%,#2dd4bf 100%);-webkit-background-clip:text;background-clip:text;color:transparent;}
.cg-sub{margin:.25rem 0 .7rem 0;color:var(--mut);font-size:1.05rem;letter-spacing:.01em;}
.cg-pills{display:flex;flex-wrap:wrap;gap:.45rem;}
.cg-pill{border:1px solid rgba(45,212,191,.28);background:rgba(45,212,191,.08);color:#99f6e4;border-radius:999px;
  padding:.18rem .7rem;font-size:.74rem;font-weight:600;letter-spacing:.03em;}
.cg-pill.muted{border-color:var(--line);background:rgba(148,163,184,.07);color:var(--mut);}

/* ---------- disclaimer ---------- */
.cg-disclaimer{
  margin:.9rem 0 0 0;padding:.85rem 1.1rem;border-radius:14px;font-family:var(--font);
  border:1px solid rgba(251,191,36,.35);border-left:5px solid var(--rev);
  background:linear-gradient(90deg,rgba(251,191,36,.12),rgba(251,191,36,.035));color:#fde68a;font-size:.93rem;line-height:1.45;
}
.cg-disclaimer b{color:#fef3c7;letter-spacing:.04em;}

/* ---------- generic cards ---------- */
.cg-card{background:linear-gradient(180deg,var(--card2),var(--card));border:1px solid var(--line);border-radius:16px;
  padding:1.05rem 1.2rem;box-shadow:0 10px 30px rgba(0,0,0,.25);font-family:var(--font);}
.cg-card h4{margin:0 0 .5rem 0;font-size:.78rem;text-transform:uppercase;letter-spacing:.1em;color:var(--mut);font-weight:700;}
.cg-card p{margin:.2rem 0;color:#cdd8ea;line-height:1.55;font-size:.95rem;}
.cg-card ul{margin:.3rem 0 0 1.1rem;padding:0;color:#cdd8ea;font-size:.92rem;line-height:1.55;}
.cg-section{font-family:var(--font);font-size:1.25rem;font-weight:750;margin:1.9rem 0 .15rem 0;letter-spacing:-.01em;color:#f1f5f9;
  display:flex;align-items:center;gap:.6rem;}
.cg-section:before{content:"";width:4px;height:1.1em;border-radius:4px;background:linear-gradient(180deg,#5eead4,#14b8a6);display:inline-block;}
.cg-section-cap{font-family:var(--font);color:var(--mut);margin:0 0 .9rem 0;font-size:.9rem;}

/* ---------- KPI ---------- */
.cg-kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(285px,1fr));gap:14px;margin:1.1rem 0 .4rem 0;}
.cg-kpi{position:relative;overflow:hidden;border-radius:16px;padding:1rem 1.15rem 1.05rem 1.15rem;font-family:var(--font);
  background:linear-gradient(180deg,var(--card2),var(--card));border:1px solid var(--line);box-shadow:0 10px 30px rgba(0,0,0,.25);
  display:flex;justify-content:space-between;align-items:center;gap:.6rem;}
.cg-kpi:before{content:"";position:absolute;left:0;right:0;top:0;height:3px;background:var(--accent,var(--teal));}
.cg-kpi-label{font-size:.72rem;text-transform:uppercase;letter-spacing:.1em;color:var(--mut);font-weight:700;}
.cg-kpi-value{font-size:2.05rem;font-weight:800;letter-spacing:-.02em;line-height:1.15;color:#f8fafc;margin-top:.15rem;}
.cg-kpi-value small{font-size:.95rem;color:var(--mut);font-weight:600;margin-left:.15rem;}
.cg-kpi-sub{font-size:.8rem;color:var(--mut);margin-top:.15rem;}
.cg-delta-up{color:var(--pass);font-weight:700;} .cg-delta-down{color:var(--fail);font-weight:700;} .cg-delta-flat{color:var(--mut);font-weight:700;}

/* ---------- badges ---------- */
.cg-badge{display:inline-flex;align-items:center;gap:.3rem;padding:.14rem .65rem;border-radius:999px;font-weight:800;
  font-size:.7rem;letter-spacing:.07em;font-family:var(--font);white-space:nowrap;}
.cg-badge.pass{color:#6ee7b7;background:rgba(52,211,153,.12);border:1px solid rgba(52,211,153,.45);}
.cg-badge.fail{color:#fca5a5;background:rgba(248,113,113,.12);border:1px solid rgba(248,113,113,.5);}
.cg-badge.review{color:#fde68a;background:rgba(251,191,36,.12);border:1px solid rgba(251,191,36,.5);}
.cg-arrow{color:var(--mut);margin:0 .35rem;}

/* ---------- pipeline flow ---------- */
.cg-flow{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;font-family:var(--font);}
.cg-step{position:relative;padding:.85rem .95rem;border-radius:14px;background:rgba(13,25,48,.85);border:1px solid var(--line);}
.cg-step .k{display:inline-flex;width:1.6rem;height:1.6rem;border-radius:8px;align-items:center;justify-content:center;
  font-weight:800;font-size:.8rem;color:#042f2e;background:linear-gradient(135deg,#5eead4,#14b8a6);margin-bottom:.4rem;}
.cg-step .t{font-weight:700;color:#f1f5f9;font-size:.93rem;}
.cg-step .d{color:var(--mut);font-size:.8rem;line-height:1.4;margin-top:.15rem;}
.cg-step.layer{border-color:rgba(45,212,191,.45);box-shadow:0 0 0 1px rgba(45,212,191,.12) inset;}

/* ---------- chat bubbles ---------- */
.cg-bubble{border-radius:14px;padding:.8rem 1rem;margin:.55rem 0;font-family:var(--font);font-size:.95rem;line-height:1.55;color:#dbe5f4;
  border:1px solid var(--line);}
.cg-bubble .lbl{display:flex;justify-content:space-between;align-items:center;gap:.6rem;font-size:.68rem;text-transform:uppercase;
  letter-spacing:.1em;font-weight:800;margin-bottom:.4rem;color:var(--mut);}
.cg-bubble.user{background:rgba(59,130,246,.10);border-color:rgba(96,165,250,.3);}
.cg-bubble.user .lbl{color:#93c5fd;}
.cg-bubble.fixture{background:rgba(148,163,184,.08);}
.cg-bubble.layer{background:rgba(45,212,191,.09);border-color:rgba(45,212,191,.4);}
.cg-bubble.layer .lbl{color:#5eead4;}
.cg-note{font-family:var(--font);color:var(--mut);font-size:.85rem;margin:.4rem 0;}

/* ---------- rule tables ---------- */
.cg-table{width:100%;border-collapse:separate;border-spacing:0;font-family:var(--font);font-size:.86rem;overflow:hidden;border-radius:12px;border:1px solid var(--line);}
.cg-table th{background:rgba(148,163,184,.09);color:var(--mut);text-align:left;font-size:.7rem;text-transform:uppercase;letter-spacing:.08em;padding:.55rem .75rem;}
.cg-table td{padding:.6rem .75rem;border-top:1px solid var(--line);color:#cdd8ea;vertical-align:top;}
.cg-evidence{margin:.35rem 0 0 0;padding:0;list-style:none;}
.cg-evidence li{font-family:var(--font);font-size:.88rem;color:#cdd8ea;padding:.4rem .7rem;margin:.3rem 0;border-radius:10px;
  background:rgba(148,163,184,.07);border-left:3px solid var(--mut);}
.cg-evidence.fail li{border-left-color:var(--fail);} .cg-evidence.review li{border-left-color:var(--rev);} .cg-evidence.pass li{border-left-color:var(--pass);}

/* ---------- chips ---------- */
.cg-chips{display:flex;flex-wrap:wrap;gap:.4rem;margin:.3rem 0 .2rem 0;}
.cg-chip{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:.78rem;padding:.14rem .55rem;border-radius:8px;
  border:1px solid var(--line);background:rgba(148,163,184,.08);color:#cbd5e1;}
.cg-chip.good{border-color:rgba(52,211,153,.45);color:#6ee7b7;background:rgba(52,211,153,.08);}
.cg-chip.bad{border-color:rgba(248,113,113,.5);color:#fca5a5;background:rgba(248,113,113,.08);}

/* ---------- empty state ---------- */
.cg-empty{font-family:var(--font);text-align:center;padding:2.4rem 1rem;border:1px dashed rgba(148,163,184,.3);border-radius:16px;
  background:rgba(13,25,48,.5);color:var(--mut);}
.cg-empty .big{font-size:1.1rem;font-weight:700;color:#e2e8f0;margin-bottom:.3rem;}

/* ---------- sidebar ---------- */
.cg-brand{display:flex;align-items:center;gap:.65rem;margin-bottom:.2rem;font-family:var(--font);}
.cg-brand .n{font-weight:800;font-size:1.2rem;letter-spacing:-.01em;color:#f1f5f9;}
.cg-brand .s{font-size:.68rem;color:var(--mut);letter-spacing:.06em;text-transform:uppercase;}
.cg-side-card{font-family:var(--font);margin:.8rem 0;padding:.8rem .9rem;border-radius:14px;border:1px solid var(--line);background:rgba(13,25,48,.7);
  font-size:.8rem;color:var(--mut);line-height:1.6;}
.cg-side-card b{color:#e2e8f0;font-weight:650;}
.cg-side-card code{color:#5eead4;background:transparent;font-size:.78rem;}
section[data-testid="stSidebar"] div[role="radiogroup"]{gap:.25rem;}
section[data-testid="stSidebar"] div[role="radiogroup"] > label{
  padding:.55rem .8rem;border-radius:10px;border:1px solid transparent;transition:all .15s ease;width:100%;}
section[data-testid="stSidebar"] div[role="radiogroup"] > label:hover{background:rgba(45,212,191,.08);}
section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked){
  background:linear-gradient(90deg,rgba(45,212,191,.20),rgba(45,212,191,.05));border-color:rgba(45,212,191,.45);}
section[data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child{display:none;}
section[data-testid="stSidebar"] div[role="radiogroup"] > label p{font-weight:650;font-size:.95rem;}

/* ---------- native widgets ---------- */
.stButton > button, .stDownloadButton > button{
  border-radius:11px;border:1px solid rgba(45,212,191,.5);background:rgba(45,212,191,.10);color:#99f6e4;font-weight:700;
  transition:all .15s ease;padding:.5rem 1rem;}
.stButton > button:hover, .stDownloadButton > button:hover{background:rgba(45,212,191,.2);border-color:#2dd4bf;color:#ecfeff;transform:translateY(-1px);}
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"]{
  background:linear-gradient(135deg,#2dd4bf,#14b8a6);color:#04211f;border:none;box-shadow:0 8px 22px rgba(20,184,166,.35);}
.stButton > button[kind="primary"]:hover{filter:brightness(1.08);color:#021412;}
[data-testid="stDataFrame"]{border:1px solid var(--line);border-radius:14px;overflow:hidden;}
[data-testid="stExpander"]{border:1px solid var(--line);border-radius:14px;background:rgba(13,25,48,.55);}
[data-baseweb="select"] > div, [data-baseweb="input"] > div{background:rgba(13,25,48,.9) !important;border-color:var(--line) !important;border-radius:11px !important;}
.stTabs [data-baseweb="tab-list"]{gap:.3rem;border-bottom:1px solid var(--line);}
.stTabs [data-baseweb="tab"]{border-radius:10px 10px 0 0;padding:.5rem 1rem;color:var(--mut);}
.stTabs [aria-selected="true"]{color:#5eead4;}
.stProgress > div > div > div > div{background:linear-gradient(90deg,#14b8a6,#5eead4);}
hr{border-color:var(--line) !important;}
</style>
"""

SHIELD_SVG = """
<svg class="cg-logo" width="{size}" height="{size}" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" aria-label="ClinGuard AI logo">
<defs><linearGradient id="cgg{uid}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#5eead4"/><stop offset="1" stop-color="#0d9488"/></linearGradient></defs>
<path d="M32 4 L54 12 V30 C54 44 44.5 54.5 32 60 C19.5 54.5 10 44 10 30 V12 Z" fill="url(#cgg{uid})"/>
<path d="M32 9 L49 15.2 V30 C49 41 41.6 49.6 32 54.4 C22.4 49.6 15 41 15 30 V15.2 Z" fill="#06182b" opacity=".92"/>
<path d="M28 20 H36 V28 H44 V36 H36 V44 H28 V36 H20 V28 H28 Z" fill="url(#cgg{uid})"/>
</svg>
"""


def esc(value: Any) -> str:
    return _html.escape("" if value is None else str(value)).replace("\n", "<br>")


def compact(markup: str) -> str:
    """Collapse indentation/newlines so Markdown never mistakes the HTML for a code block."""
    return "".join(line.strip() for line in markup.strip().splitlines())


def logo(size: int = 64, uid: str = "a") -> str:
    return compact(SHIELD_SVG.format(size=size, uid=uid))


def pretty(text: str) -> str:
    return (text or "").replace("_", " ")


def badge(status: str) -> str:
    cls = STATUS_CLASS.get(status, "review")
    label = STATUS_TEXT.get(status, esc(status))
    return f'<span class="cg-badge {cls}">{STATUS_ICON.get(status, "")} {label}</span>'


def transition_badges(before: str, after: str) -> str:
    return f'{badge(before)}<span class="cg-arrow">&rarr;</span>{badge(after)}'


def section(title: str, caption: str = "") -> str:
    cap = f'<div class="cg-section-cap">{esc(caption)}</div>' if caption else ""
    return compact(f'<div class="cg-section">{esc(title)}</div>') + cap


def hero(metadata: dict[str, Any] | None) -> str:
    meta = metadata or {}
    pills = ['<span class="cg-pill">Offline &middot; no API keys</span>',
             '<span class="cg-pill">Deterministic rules</span>',
             '<span class="cg-pill">Fixture-based &middot; not live red-teaming</span>']
    if meta.get("n_cases"):
        pills.append(f'<span class="cg-pill muted">{meta["n_cases"]} fictional cases</span>')
    if meta.get("run_id"):
        pills.append(f'<span class="cg-pill muted">run {esc(meta["run_id"])}</span>')
    return compact(f"""
    <div class="cg-hero">
      {logo(74, "hero")}
      <div>
        <h1 class="cg-title">{esc(APP_NAME)}</h1>
        <div class="cg-sub">{esc(APP_SUBTITLE)}</div>
        <div class="cg-pills">{''.join(pills)}</div>
      </div>
    </div>""")


def disclaimer() -> str:
    return compact(f"""
    <div class="cg-disclaimer"><b>&#9888; EDUCATIONAL PROTOTYPE</b> &mdash; {esc(DISCLAIMER_SHORT.split(' - ', 1)[1])}
    &nbsp;Figures describe the included demonstration benchmark only, not real-world clinical safety rates.</div>""")


def ring(percent: float, color: str = "#2dd4bf", size: int = 74) -> str:
    pct = max(0.0, min(100.0, percent))
    return compact(f"""
    <svg width="{size}" height="{size}" viewBox="0 0 36 36" style="flex:0 0 auto">
      <circle cx="18" cy="18" r="15.9155" fill="none" stroke="rgba(148,163,184,.16)" stroke-width="3.2"/>
      <circle cx="18" cy="18" r="15.9155" fill="none" stroke="{color}" stroke-width="3.2" stroke-linecap="round"
              stroke-dasharray="{pct:.2f} {100 - pct:.2f}" transform="rotate(-90 18 18)"/>
      <text x="18" y="20.6" text-anchor="middle" font-size="7.4" font-weight="800" fill="#f1f5f9"
            font-family="system-ui,Segoe UI,Arial,sans-serif">{pct:.0f}%</text>
    </svg>""")


def kpi(label: str, value: str, sub: str = "", accent: str = "#2dd4bf", percent: float | None = None,
        unit: str = "") -> str:
    unit_html = f"<small>{esc(unit)}</small>" if unit else ""
    ring_html = ring(percent, accent) if percent is not None else ""
    return compact(f"""
    <div class="cg-kpi" style="--accent:{accent}">
      <div><div class="cg-kpi-label">{esc(label)}</div>
      <div class="cg-kpi-value">{esc(value)}{unit_html}</div>
      <div class="cg-kpi-sub">{sub}</div></div>{ring_html}
    </div>""")


def kpi_row(items: Iterable[str], cols: int | None = None) -> str:
    style = f' style="grid-template-columns:repeat({cols},minmax(0,1fr))"' if cols else ""
    return f'<div class="cg-kpis"{style}>{"".join(items)}</div>'


def delta_html(delta: float, unit: str = "pp", good_when_positive: bool = True) -> str:
    if abs(delta) < 1e-9:
        return f'<span class="cg-delta-flat">no change</span>'
    up = delta > 0
    good = up == good_when_positive
    cls = "cg-delta-up" if good else "cg-delta-down"
    arrow = "&#9650;" if up else "&#9660;"
    return f'<span class="{cls}">{arrow} {abs(delta):.1f} {unit}</span>'


def pipeline_flow() -> str:
    steps = [
        ("A", "Case loading", "29 fictional cases with stable IDs and explicit criteria", False),
        ("B", "Baseline fixtures", "Hand-written responses; no model is called", False),
        ("C", "Evaluator", "Transparent regex rules give PASS / FAIL / NEEDS REVIEW", False),
        ("D", "Safety layer", "Deterministic safeguards; never sees the answer key", True),
        ("E", "Re-evaluation", "Evaluator re-runs on the transformed response", False),
        ("F", "Metrics & audit", "Counts, denominators and exports from real results", False),
    ]
    cards = "".join(
        f'<div class="cg-step{" layer" if layer else ""}"><div class="k">{k}</div><div class="t">{esc(t)}</div><div class="d">{esc(d)}</div></div>'
        for k, t, d, layer in steps)
    return f'<div class="cg-flow">{cards}</div>'


def bubble(kind: str, label: str, text: str, right: str = "") -> str:
    return compact(f'<div class="cg-bubble {kind}"><div class="lbl"><span>{esc(label)}</span><span>{right}</span></div>{esc(text)}</div>')


def card(title: str, body_html: str) -> str:
    return compact(f'<div class="cg-card"><h4>{esc(title)}</h4>{body_html}</div>')


def evidence_list(items: Sequence[str], status: str) -> str:
    cls = STATUS_CLASS.get(status, "review")
    lis = "".join(f"<li>{esc(i)}</li>" for i in items) or "<li>No evidence recorded.</li>"
    return f'<ul class="cg-evidence {cls}">{lis}</ul>'


def rules_table(rules: Sequence[dict[str, Any]]) -> str:
    if not rules:
        return '<div class="cg-note">No rule-level results were recorded for this case.</div>'
    rows = "".join(
        f'<tr><td><span class="cg-chip">{esc(r.get("rule_id"))}</span></td><td>{esc(r.get("description"))}</td>'
        f'<td>{badge(r.get("outcome", ""))}</td><td>{esc(r.get("evidence"))}</td></tr>'
        for r in rules)
    return compact(f'<table class="cg-table"><thead><tr><th>Rule</th><th>Criterion</th><th>Outcome</th><th>Evidence</th></tr></thead><tbody>{rows}</tbody></table>')


def chips(ids: Iterable[str], kind: str = "") -> str:
    ids = list(ids)
    if not ids:
        return '<div class="cg-note">None.</div>'
    return '<div class="cg-chips">' + "".join(f'<span class="cg-chip {kind}">{esc(i)}</span>' for i in ids) + "</div>"


def empty_state(title: str, message: str) -> str:
    return compact(f'<div class="cg-empty"><div class="big">{esc(title)}</div><div>{esc(message)}</div></div>')


def sidebar_brand() -> str:
    return compact(f'<div class="cg-brand">{logo(38, "side")}<div><div class="n">{esc(APP_NAME)}</div><div class="s">Safety evaluation workbench</div></div></div>')


def sidebar_run_card(metadata: dict[str, Any] | None) -> str:
    if not metadata:
        return '<div class="cg-side-card">No run yet.</div>'
    scope = metadata.get("categories_filter")
    scope_text = "full benchmark" if scope == "all" else f"{len(scope)} categor{'y' if len(scope) == 1 else 'ies'}"
    return compact(f"""
    <div class="cg-side-card">
      <b>Current run</b><br>
      id <code>{esc(metadata.get('run_id'))}</code><br>
      scope <b>{esc(scope_text)}</b> &middot; {esc(metadata.get('n_cases'))} cases<br>
      provider <code>{esc(metadata.get('provider'))}</code><br>
      {esc(metadata.get('generated_at_utc'))}
    </div>""")


def sidebar_footer() -> str:
    return compact(f'<div class="cg-side-card">{esc(EVALUATION_MODE)}</div>')

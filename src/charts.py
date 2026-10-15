
"""Plotly figures styled for the dark-navy theme. Every value is computed from run records."""

from __future__ import annotations

from typing import Any, Sequence

import plotly.graph_objects as go

from . import metrics

COLORS = {
    "PASS": "#34d399",
    "FAIL": "#f87171",
    "NEEDS_REVIEW": "#fbbf24",
    "teal": "#2dd4bf",
    "slate": "#64748b",
    "text": "#cbd5e1",
    "grid": "rgba(148,163,184,.13)",
}
LABELS = {"PASS": "PASS", "FAIL": "FAIL", "NEEDS_REVIEW": "NEEDS REVIEW"}
FONT = "Inter, Segoe UI, system-ui, -apple-system, Roboto, Arial, sans-serif"


def _style(fig: go.Figure, height: int = 360, legend: bool = True) -> go.Figure:
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=COLORS["text"], family=FONT, size=13),
        margin=dict(l=8, r=8, t=34, b=8),
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor="#0e1a31", bordercolor="#2dd4bf", font=dict(color="#e6edf7", family=FONT)),
    )
    fig.update_xaxes(gridcolor=COLORS["grid"], zeroline=False, linecolor=COLORS["grid"])
    fig.update_yaxes(gridcolor=COLORS["grid"], zeroline=False, linecolor=COLORS["grid"])
    return fig


def category_outcomes(records: Sequence[dict[str, Any]], stage: str) -> go.Figure:
    """Stacked horizontal bars: outcome counts per category at `stage`."""
    rows = metrics.by_category(records, stage)
    categories = [r["category"] for r in rows]
    fig = go.Figure()
    for key, field in (("PASS", "pass"), ("NEEDS_REVIEW", "review"), ("FAIL", "fail")):
        fig.add_bar(
            y=categories, x=[r[field] for r in rows], name=LABELS[key], orientation="h",
            marker=dict(color=COLORS[key], line=dict(color="#0a1224", width=2)),
            text=[r[field] if r[field] else "" for r in rows], textposition="inside",
            textfont=dict(color="#04141a", size=13), insidetextanchor="middle",
            hovertemplate="%{y}<br>" + LABELS[key] + ": %{x}<extra></extra>",
        )
    fig.update_layout(barmode="stack", bargap=0.35)
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(title_text="Cases", dtick=1)
    return _style(fig, height=max(320, 44 * len(categories) + 90))


def status_compare(before_after: dict[str, Any]) -> go.Figure:
    """Grouped bars: baseline vs after-layer status counts."""
    keys = ("PASS", "FAIL", "NEEDS_REVIEW")
    fields = ("pass", "fail", "review")
    labels = [LABELS[k] for k in keys]
    base = [before_after["baseline"][f] for f in fields]
    final = [before_after["final"][f] for f in fields]
    fig = go.Figure()
    fig.add_bar(x=labels, y=base, name="Baseline", marker_color=COLORS["slate"], text=base, textposition="outside",
                hovertemplate="Baseline %{x}: %{y}<extra></extra>")
    fig.add_bar(x=labels, y=final, name="After safety layer", marker_color=COLORS["teal"], text=final, textposition="outside",
                hovertemplate="After layer %{x}: %{y}<extra></extra>")
    fig.update_layout(barmode="group", bargap=0.3, bargroupgap=0.08)
    fig.update_yaxes(title_text="Cases", range=[0, max(base + final + [1]) * 1.18])
    return _style(fig, height=340)


def category_pass_rate(records: Sequence[dict[str, Any]]) -> go.Figure:
    base_rows = {r["category"]: r for r in metrics.by_category(records, "baseline")}
    final_rows = metrics.by_category(records, "final")
    categories = [r["category"] for r in final_rows]
    base_vals = [100 * base_rows[c]["pass_rate"] for c in categories]
    final_vals = [100 * r["pass_rate"] for r in final_rows]
    fig = go.Figure()
    fig.add_bar(y=categories, x=base_vals, name="Baseline", orientation="h", marker_color=COLORS["slate"],
                text=[f'{base_rows[c]["pass"]}/{base_rows[c]["total"]}' for c in categories], textposition="outside",
                hovertemplate="%{y}<br>Baseline pass rate: %{x:.1f}%<extra></extra>")
    fig.add_bar(y=categories, x=final_vals, name="After safety layer", orientation="h", marker_color=COLORS["teal"],
                text=[f'{r["pass"]}/{r["total"]}' for r in final_rows], textposition="outside",
                hovertemplate="%{y}<br>After-layer pass rate: %{x:.1f}%<extra></extra>")
    fig.update_layout(barmode="group", bargap=0.28, bargroupgap=0.06)
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(title_text="Pass rate (%)", range=[0, 118], ticksuffix="%")
    return _style(fig, height=max(420, 62 * len(categories) + 80))


def sankey(transitions: dict[tuple[str, str], int]) -> go.Figure:
    order = ("PASS", "FAIL", "NEEDS_REVIEW")
    labels = [f"Baseline - {LABELS[s]}" for s in order] + [f"After layer - {LABELS[s]}" for s in order]
    node_colors = [COLORS[s] for s in order] * 2
    sources, targets, values, link_colors = [], [], [], []
    for i, before in enumerate(order):
        for j, after in enumerate(order):
            count = transitions.get((before, after), 0)
            if count:
                sources.append(i)
                targets.append(3 + j)
                values.append(count)
                hexcolor = COLORS[after].lstrip("#")
                r, g, b = (int(hexcolor[k:k + 2], 16) for k in (0, 2, 4))
                link_colors.append(f"rgba({r},{g},{b},.38)")
    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(label=labels, color=node_colors, pad=22, thickness=18, line=dict(color="#0a1224", width=1)),
        link=dict(source=sources, target=targets, value=values, color=link_colors,
                  hovertemplate="%{source.label} -> %{target.label}: %{value} cases<extra></extra>"),
    ))
    return _style(fig, height=340, legend=False)


def donut(summary: dict[str, Any], center_text: str = "") -> go.Figure:
    keys = ("PASS", "FAIL", "NEEDS_REVIEW")
    values = [summary["pass"], summary["fail"], summary["review"]]
    fig = go.Figure(go.Pie(
        labels=[LABELS[k] for k in keys], values=values, hole=0.68, sort=False, direction="clockwise",
        marker=dict(colors=[COLORS[k] for k in keys], line=dict(color="#0a1224", width=3)),
        textinfo="value", textfont=dict(color="#04141a", size=13),
        hovertemplate="%{label}: %{value} of " + str(summary["total"]) + " cases<extra></extra>",
    ))
    if center_text:
        fig.add_annotation(text=center_text, showarrow=False, font=dict(size=22, color="#f8fafc", family=FONT))
    return _style(fig, height=300, legend=True)

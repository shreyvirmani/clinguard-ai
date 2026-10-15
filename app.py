"""ClinGuard AI - Healthcare AI Safety Evaluation Workbench (Streamlit dashboard).

EDUCATIONAL PROTOTYPE. Offline, fixture-based evaluation. Not live LLM red-teaming.
Run with:  streamlit run app.py
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src import charts, metrics, ui
from src.benchmark import CATEGORY_ORDER, get_builtin_cases
from src.constants import (APP_NAME, APP_SUBTITLE, DISCLAIMER_LONG, EVALUATION_MODE, IMPLEMENTED, LIMITATIONS,
                           NOT_IMPLEMENTED)
from src.pipeline import RunResult, run_benchmark
from src.reporting import build_markdown_report, to_csv, to_json
from src.safety_layer import SAFEGUARD_DESCRIPTIONS

st.set_page_config(page_title=f"{APP_NAME} | {APP_SUBTITLE}", page_icon="\U0001F6E1️", layout="wide",
                   initial_sidebar_state="expanded")
st.markdown(ui.CSS, unsafe_allow_html=True)

PAGES = ["Overview", "Run Tests", "Failure Analysis", "Before vs After", "Audit Report"]
STATUS_FILTERS = {"All": None, "FAIL": "FAIL", "NEEDS REVIEW": "NEEDS_REVIEW", "PASS": "PASS"}
STATUS_WORD = {"PASS": "PASS", "FAIL": "FAIL", "NEEDS_REVIEW": "NEEDS REVIEW"}
PLOT_CONFIG = {"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]}


# ---------------------------------------------------------------------------------- state
def execute_run(categories: list[str] | None = None, progress=None) -> RunResult:
    """Run the full pipeline and store the outcome in session state."""
    result = run_benchmark(categories=categories or None, progress_callback=progress)
    st.session_state["result"] = result
    st.session_state["run_error"] = None
    return result


def ensure_initial_run() -> None:
    if "result" in st.session_state:
        return
    try:
        with st.spinner("Running the benchmark offline..."):
            execute_run()
    except Exception as exc:  # pragma: no cover - defensive; surfaced in the UI
        st.session_state["result"] = None
        st.session_state["run_error"] = f"{type(exc).__name__}: {exc}"


def current() -> RunResult | None:
    return st.session_state.get("result")


def md(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


def plot(fig) -> None:
    st.plotly_chart(fig, use_container_width=True, config=PLOT_CONFIG)


def require_results() -> RunResult | None:
    """Return the current run or render a friendly empty / error state."""
    if st.session_state.get("run_error"):
        st.error(f"The benchmark could not be run: {st.session_state['run_error']}")
    result = current()
    if result is None or not result.records:
        md(ui.empty_state("No results yet", "Open Run Tests and run the benchmark, or use the sidebar button."))
        for message in (result.errors if result else []):
            st.warning(message)
        return None
    return result


def records_frame(records: list[dict]) -> pd.DataFrame:
    return pd.DataFrame([{
        "Case": r["case_id"],
        "Category": r["category"],
        "Title": r["title"],
        "Baseline": STATUS_WORD.get(r["baseline_status"], r["baseline_status"]),
        "Safeguard applied": r["safeguard_applied"].replace("_", " ") or "-",
        "After layer": STATUS_WORD.get(r["final_status"], r["final_status"]),
        "Failure category": ui.pretty(r["final_failure_category"] or r["baseline_failure_category"]) or "-",
    } for r in records])


STATUS_STYLES = {
    "PASS": "background-color: rgba(52,211,153,.16); color: #6ee7b7; font-weight: 700",
    "FAIL": "background-color: rgba(248,113,113,.16); color: #fca5a5; font-weight: 700",
    "NEEDS REVIEW": "background-color: rgba(251,191,36,.16); color: #fde68a; font-weight: 700",
}


def style_status(value: str) -> str:
    return STATUS_STYLES.get(value, "")


def show_table(records: list[dict], height: int = 420) -> None:
    frame = records_frame(records)
    styler = frame.style.map(style_status, subset=["Baseline", "After layer"])
    st.dataframe(styler, use_container_width=True, hide_index=True, height=height)


# ---------------------------------------------------------------------------------- sidebar
ensure_initial_run()
result = current()

with st.sidebar:
    md(ui.sidebar_brand())
    st.write("")
    page = st.radio("Navigation", PAGES, key="page", label_visibility="collapsed")
    st.write("")
    if st.button("↻  Rerun full benchmark", use_container_width=True, type="primary", key="side_rerun"):
        try:
            with st.spinner("Re-running all cases..."):
                result = execute_run()
            st.toast("Benchmark re-run complete", icon="✅")
        except Exception as exc:
            st.session_state["run_error"] = f"{type(exc).__name__}: {exc}"
    md(ui.sidebar_run_card(result.metadata if result else None))
    if result and result.records:
        st.download_button("⬇  Export results (CSV)", to_csv(result.records, result.metadata),
                           file_name=f"clinguard_results_{result.metadata['run_id']}.csv", mime="text/csv",
                           use_container_width=True, key="side_csv")
    md(ui.sidebar_footer())

# ---------------------------------------------------------------------------------- header
md(ui.hero(result.metadata if result else None))
md(ui.disclaimer())


# ---------------------------------------------------------------------------------- pages
def page_overview() -> None:
    records_result = require_results()
    if not records_result:
        return
    records = records_result.records
    ba = metrics.before_after(records)
    base, final = ba["baseline"], ba["final"]
    split = metrics.split_by_kind(records)
    benign_final = ba["benign_final"]

    md(ui.section("Current run summary", "Baseline = hand-written fixture responses. After layer = deterministic safety layer, re-evaluated."))
    delta_pp = 100 * ba["pass_rate_delta"]
    md(ui.kpi_row([
        ui.kpi("Benchmark size", f'{base["total"]}', f'{len(records) - split["benign"]["baseline"]["total"]} adversarial &middot; {split["benign"]["baseline"]["total"]} benign',
               "#60a5fa", unit="cases"),
        ui.kpi("Baseline pass rate", f'{100 * base["pass_rate"]:.1f}%', f'{base["pass"]}/{base["total"]} cases pass', "#64748b",
               percent=100 * base["pass_rate"]),
        ui.kpi("After safety layer", f'{100 * final["pass_rate"]:.1f}%',
               f'{final["pass"]}/{final["total"]} pass &middot; {ui.delta_html(delta_pp)}', "#2dd4bf", percent=100 * final["pass_rate"]),
        ui.kpi("Failure rate (after)", f'{100 * final["fail_rate"]:.1f}%', f'{final["fail"]}/{final["total"]} cases fail', "#f87171"),
        ui.kpi("Human-review rate", f'{100 * final["review_rate"]:.1f}%', f'{final["review"]}/{final["total"]} need review', "#fbbf24"),
        ui.kpi("Benign false positives", f'{benign_final["benign_not_passing"]}/{benign_final["benign_total"]}',
               f'{100 * benign_final["rate"]:.1f}% of benign cases not passing', "#a78bfa"),
    ], cols=3))

    left, right = st.columns([3, 2], gap="large")
    with left:
        md(ui.section("Outcomes by category", "Counts per category after the safety layer (hover for detail)."))
        plot(charts.category_outcomes(records, "final"))
    with right:
        md(ui.section("Overall outcome mix", "After safety layer."))
        plot(charts.donut(final, f'{final["pass"]}/{final["total"]}'))
        md(ui.card("Scope", "<p>All figures are computed from this run of the included demonstration benchmark. "
                            "They are <b>not</b> real-world clinical safety rates.</p>"))

    md(ui.section("Category breakdown", "Raw counts with denominators."))
    after_rows = {r["category"]: r for r in metrics.by_category(records, "final")}
    table = pd.DataFrame([{
        "Category": r["category"],
        "Cases": r["total"],
        "Baseline pass": metrics.fmt_ratio(r["pass"], r["total"]),
        "After-layer pass": metrics.fmt_ratio(after_rows[r["category"]]["pass"], r["total"]),
        "After: fail": after_rows[r["category"]]["fail"],
        "After: review": after_rows[r["category"]]["review"],
    } for r in metrics.by_category(records, "baseline")])
    st.dataframe(table, use_container_width=True, hide_index=True)

    md(ui.section("How the pipeline works", "Evaluation and intervention are separate modules; success is never assumed."))
    md(ui.pipeline_flow())
    md(f'<p class="cg-note">{ui.esc(EVALUATION_MODE)}</p>')


def page_run_tests() -> None:
    md(ui.section("Run tests", "Run the whole benchmark or only selected categories. Runs are deterministic and fully offline."))
    cases = get_builtin_cases()
    counts = {c: sum(1 for case in cases if case.category == c) for c in CATEGORY_ORDER}
    with st.container():
        chosen = st.multiselect("Categories (leave empty to run every category)", CATEGORY_ORDER,
                                format_func=lambda c: f"{c}  ({counts[c]})", key="category_filter")
        c1, c2, c3 = st.columns([1.3, 1.3, 3])
        run_selected = c1.button("▶  Run benchmark", type="primary", use_container_width=True, key="run_btn")
        run_all = c2.button("↻  Rerun everything", use_container_width=True, key="run_all_btn")
        n_selected = sum(counts[c] for c in chosen) if chosen else len(cases)
        c3.markdown(f'<p class="cg-note" style="margin-top:.7rem">{n_selected} of {len(cases)} cases will run.</p>', unsafe_allow_html=True)

    if run_selected or run_all:
        categories = None if run_all else (chosen or None)
        bar = st.progress(0.0, text="Starting...")

        def on_progress(done: int, total: int, case_id: str) -> None:
            bar.progress(done / total, text=f"Evaluating {case_id}  ({done}/{total})")

        try:
            with st.spinner("Evaluating baseline, applying the safety layer, re-evaluating..."):
                run = execute_run(categories, on_progress)
            bar.empty()
            if run.records:
                st.success(f"Run {run.metadata['run_id']} finished: {len(run.records)} cases evaluated.")
            for message in run.errors:
                st.warning(message)
        except Exception as exc:
            bar.empty()
            st.session_state["run_error"] = f"{type(exc).__name__}: {exc}"
            st.error(f"The run failed: {exc}")

    run = require_results()
    if not run:
        return
    records = run.records
    final = metrics.summarize(records, "final")
    base = metrics.summarize(records, "baseline")
    md(ui.kpi_row([
        ui.kpi("Cases run", str(final["total"]), f'run <code>{ui.esc(run.metadata["run_id"])}</code>', "#60a5fa"),
        ui.kpi("Pass", metrics.fmt_ratio(final["pass"], final["total"]), f'baseline {metrics.fmt_ratio(base["pass"], base["total"])}', "#34d399"),
        ui.kpi("Fail", metrics.fmt_ratio(final["fail"], final["total"]), f'baseline {metrics.fmt_ratio(base["fail"], base["total"])}', "#f87171"),
        ui.kpi("Needs review", metrics.fmt_ratio(final["review"], final["total"]), f'baseline {metrics.fmt_ratio(base["review"], base["total"])}', "#fbbf24"),
    ], cols=4))
    md(ui.section("Results", "Status before and after the safety layer for every case in this run."))
    filter_choice = st.radio("Show", list(STATUS_FILTERS), horizontal=True, key="run_status_filter",
                             help="Filters on the status AFTER the safety layer.")
    wanted = STATUS_FILTERS[filter_choice]
    shown = [r for r in records if wanted is None or r["final_status"] == wanted]
    if shown:
        show_table(shown, height=min(640, 60 + 36 * len(shown)))
    else:
        md(ui.empty_state("Nothing matches this filter", "Choose another status filter."))
    md('<p class="cg-note">Baseline responses are controlled demonstration fixtures, not output from a real model.</p>')


def page_failure_analysis() -> None:
    run = require_results()
    if not run:
        return
    records = run.records
    md(ui.section("Failure analysis", "Pick a sample case to inspect its input, expected behavior, response, rule-level evidence and outcome."))

    f1, f2 = st.columns([1, 2])
    status_choice = f1.selectbox("Filter by status after layer", list(STATUS_FILTERS), key="fa_filter")
    wanted = STATUS_FILTERS[status_choice]
    pool = [r for r in records if wanted is None or r["final_status"] == wanted]
    if not pool:
        md(ui.empty_state("No cases with this status", "Choose a different filter."))
        return
    ids = [r["case_id"] for r in pool]
    if st.session_state.get("fa_case") not in ids:
        st.session_state["fa_case"] = ids[0]
    by_id = {r["case_id"]: r for r in pool}
    case_id = f2.selectbox("Sample case", ids, key="fa_case",
                           format_func=lambda i: f'{i}  -  {by_id[i]["title"]}  [{STATUS_WORD[by_id[i]["baseline_status"]]} → {STATUS_WORD[by_id[i]["final_status"]]}]')
    r = by_id[case_id]

    md(compact_header(r))
    left, right = st.columns(2, gap="large")
    with left:
        md(ui.bubble("user", "User input (fictional)", r["input"]))
        md(ui.card("Expected safe behavior", f'<p>{ui.esc(r["expected_behavior"])}</p>'))
        md(ui.bubble("fixture", "Baseline response - demonstration fixture", r["baseline_response"], ui.badge(r["baseline_status"])))
    with right:
        if r["response_changed"]:
            md(ui.bubble("layer", f'After safety layer - {ui.pretty(r["safeguard_applied"])}', r["final_response"], ui.badge(r["final_status"])))
        else:
            md(ui.bubble("layer", "After safety layer - unchanged (no safeguard fired)", r["final_response"], ui.badge(r["final_status"])))
        if r["safety_reasons"]:
            md(ui.card("Why the safety layer reacted", "<ul>" + "".join(f"<li>{ui.esc(x)}</li>" for x in r["safety_reasons"]) + "</ul>"))
        else:
            md('<p class="cg-note">The safety layer found nothing it has a safeguard for in this case.</p>')

    tab_after, tab_before = st.tabs(["Evaluation after safety layer", "Baseline evaluation"])
    for tab, stage in ((tab_after, "final"), (tab_before, "baseline")):
        with tab:
            status = r[f"{stage}_status"]
            category = r[f"{stage}_failure_category"]
            md(f'<div style="margin:.4rem 0">{ui.badge(status)} '
               + (f'<span class="cg-chip bad">{ui.esc(ui.pretty(category))}</span>' if category else '<span class="cg-chip good">no failure</span>') + "</div>")
            md(f'<p class="cg-note"><b>Applicable criterion:</b> {ui.esc(r[f"{stage}_criterion"])}</p>')
            md(ui.evidence_list(r[f"{stage}_evidence"], status))
            with st.expander("Rule-by-rule results"):
                md(ui.rules_table(r[f"{stage}_rules"]))

    if r["final_status"] == "FAIL":
        st.error("This case still FAILS after the safety layer. The layer does not guarantee success; this failure is reported, not hidden.")
    elif r["final_status"] == "NEEDS_REVIEW":
        st.warning("This case needs human review: the rule-based evaluator cannot resolve the ambiguity automatically.")
    if r["is_benign"] and r["baseline_status"] == "PASS" and r["final_status"] != "PASS":
        st.error("False positive: this benign question was answered well at baseline, but the safety layer made it worse.")
    md('<p class="cg-note">The evaluator matches surface text with explicit rules. It does not understand medical meaning.</p>')


def compact_header(r: dict) -> str:
    return ui.compact(f"""
    <div class="cg-card" style="margin:.6rem 0 .8rem 0">
      <div style="display:flex;flex-wrap:wrap;gap:.6rem;align-items:center;justify-content:space-between">
        <div><span class="cg-chip">{ui.esc(r["case_id"])}</span> <span class="cg-chip">{ui.esc(r["category"])}</span>
        <span class="cg-chip">{"benign" if r["is_benign"] else "adversarial"}</span>
        <div style="font-size:1.25rem;font-weight:750;margin-top:.45rem;color:#f1f5f9">{ui.esc(r["title"])}</div></div>
        <div>{ui.transition_badges(r["baseline_status"], r["final_status"])}</div>
      </div>
    </div>""")


def page_before_after() -> None:
    run = require_results()
    if not run:
        return
    records = run.records
    ba = metrics.before_after(records)
    base, final = ba["baseline"], ba["final"]
    md(ui.section("Before vs after the safety layer", "Both columns come from the same evaluator; the 'after' column evaluates the layer's actual output."))
    md(ui.kpi_row([
        ui.kpi("Pass rate", f'{100 * final["pass_rate"]:.1f}%',
               f'{final["pass"]}/{final["total"]} vs baseline {base["pass"]}/{base["total"]} ({100 * base["pass_rate"]:.1f}%) &middot; {ui.delta_html(100 * ba["pass_rate_delta"])}', "#2dd4bf", percent=100 * final["pass_rate"]),
        ui.kpi("Cases fixed", str(len(ba["fixed_ids"])), f'out of {base["fail"] + base["review"]} non-passing at baseline', "#34d399"),
        ui.kpi("Regressions", str(len(ba["regressed_ids"])), "passed at baseline, not after the layer", "#f87171"),
        ui.kpi("Benign false positives",
               f'{ba["benign_final"]["benign_not_passing"]}/{ba["benign_final"]["benign_total"]}',
               f'baseline {ba["benign_baseline"]["benign_not_passing"]}/{ba["benign_baseline"]["benign_total"]} &middot; harmed by layer: {len(ba["layer_induced_false_positive_ids"])}', "#a78bfa"),
        ui.kpi("Remaining failures", f'{final["fail"]}/{final["total"]}', f'{final["review"]} more need human review', "#fbbf24"),
        ui.kpi("Responses changed", f'{len(ba["changed_ids"])}/{final["total"]}', "cases where a safeguard replaced the response", "#60a5fa"),
    ], cols=3))

    c1, c2 = st.columns(2, gap="large")
    with c1:
        md(ui.section("Outcome counts"))
        plot(charts.status_compare(ba))
    with c2:
        md(ui.section("Where each case moved"))
        plot(charts.sankey(ba["transitions"]))

    md(ui.section("Pass rate by category", "Labels show passes/total for each category."))
    plot(charts.category_pass_rate(records))

    md(ui.section("What the safety layer did"))
    k1, k2, k3 = st.columns(3, gap="medium")
    with k1:
        md(ui.card("Fixed by the layer", ui.chips(ba["fixed_ids"], "good")))
    with k2:
        md(ui.card("Regressions / benign cases harmed", ui.chips(sorted(set(ba["regressed_ids"]) | set(ba["layer_induced_false_positive_ids"])), "bad")))
    with k3:
        md(ui.card("Layer left unchanged", ui.chips([r["case_id"] for r in records if not r["response_changed"]])))

    md(ui.section("Remaining failures", "Cases that still FAIL after the safety layer, with the evidence."))
    remaining = metrics.remaining_failures(records)
    if not remaining:
        md(ui.empty_state("No remaining failures", "Every case passed or needs review on this run."))
    for r in remaining:
        label = f'{r["case_id"]} - {r["title"]}  |  {ui.pretty(r["final_failure_category"])}'
        with st.expander(label):
            md(ui.transition_badges(r["baseline_status"], r["final_status"]))
            md(ui.evidence_list(r["final_evidence"], "FAIL"))
            md(f'<p class="cg-note">{ui.esc(r["final_criterion"])}</p>')

    md(ui.section("Safeguards available in the layer", "Anything outside these safeguards is left unchanged."))
    rows = pd.DataFrame([{"Safeguard": k.replace("_", " "), "What it does": v,
                          "Times applied in this run": sum(1 for r in records if r["safeguard_applied"] == k)}
                         for k, v in SAFEGUARD_DESCRIPTIONS.items()])
    st.dataframe(rows, use_container_width=True, hide_index=True)


def page_audit() -> None:
    run = require_results()
    if not run:
        return
    records = run.records
    md(ui.section("Audit report", "Export the complete, reproducible results and read what this prototype does and does not show."))
    c1, c2, c3 = st.columns(3)
    stem = f'clinguard_{run.metadata["run_id"]}'
    c1.download_button("⬇  Download CSV", to_csv(records, run.metadata), file_name=f"{stem}.csv", mime="text/csv",
                       use_container_width=True, type="primary", key="dl_csv")
    c2.download_button("⬇  Download JSON", to_json(records, run.metadata), file_name=f"{stem}.json",
                       mime="application/json", use_container_width=True, key="dl_json")
    report = build_markdown_report(records, run.metadata)
    c3.download_button("⬇  Download report (.md)", report, file_name=f"{stem}_report.md", mime="text/markdown",
                       use_container_width=True, key="dl_md")

    md(ui.section("Run metadata"))
    meta = {k: v for k, v in run.metadata.items() if k != "disclaimer"}
    st.dataframe(pd.DataFrame([{"Field": k, "Value": str(v)} for k, v in meta.items()]),
                 use_container_width=True, hide_index=True)

    md(ui.section("Detailed results"))
    show_table(records, height=480)

    md(ui.section("Limitations"))
    md(ui.card("Read before citing any number", "<ul>" + "".join(f"<li>{ui.esc(x)}</li>" for x in LIMITATIONS) + "</ul>"))
    i1, i2 = st.columns(2, gap="medium")
    with i1:
        md(ui.card("Implemented", "<ul>" + "".join(f"<li>{ui.esc(x)}</li>" for x in IMPLEMENTED) + "</ul>"))
    with i2:
        md(ui.card("Not implemented", "<ul>" + "".join(f"<li>{ui.esc(x)}</li>" for x in NOT_IMPLEMENTED) + "</ul>"))
    md(f'<p class="cg-note">{ui.esc(DISCLAIMER_LONG)}</p>')
    with st.expander("Preview the Markdown audit report"):
        st.markdown(report)


PAGE_FUNCS = {
    "Overview": page_overview,
    "Run Tests": page_run_tests,
    "Failure Analysis": page_failure_analysis,
    "Before vs After": page_before_after,
    "Audit Report": page_audit,
}

try:
    PAGE_FUNCS[page]()
except Exception as exc:  # last-resort guard so a rendering bug shows a message instead of a stack trace
    st.error(f"Something went wrong while rendering this page: {type(exc).__name__}: {exc}")

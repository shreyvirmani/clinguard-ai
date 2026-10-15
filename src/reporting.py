"""Component F (part 2): exports and the audit report. Handles empty input gracefully."""

from __future__ import annotations

import csv
import io
import json
from typing import Any, Sequence

from . import metrics
from .constants import (DISCLAIMER_LONG, EVALUATION_MODE, IMPLEMENTED, LIMITATIONS, NOT_IMPLEMENTED)

CSV_COLUMNS = [
    "case_id", "category", "title", "is_benign", "input", "expected_behavior",
    "baseline_response", "baseline_status", "baseline_failure_category", "baseline_evidence", "baseline_criterion",
    "safeguard_applied", "safeguards_detected", "response_changed",
    "final_response", "final_status", "final_failure_category", "final_evidence", "final_criterion",
    "outcome_change",
]


def _flat(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        return " | ".join(str(v) for v in value)
    return "" if value is None else str(value)


def to_csv(records: Sequence[dict[str, Any]], metadata: dict[str, Any] | None = None) -> str:
    """CSV with one row per case. Always includes the header, even for an empty run."""
    buffer = io.StringIO()
    columns = (["run_id"] if metadata else []) + CSV_COLUMNS
    writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for record in records:
        row = {col: _flat(record.get(col)) for col in CSV_COLUMNS}
        if metadata:
            row["run_id"] = metadata.get("run_id", "")
        writer.writerow(row)
    return buffer.getvalue()


def summary_block(records: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """The summary that is embedded in the JSON export (all numbers computed from `records`)."""
    return {
        "scope_note": "Performance on the included demonstration benchmark only; not real-world clinical safety rates.",
        "cases": len(records),
        "before_after": metrics.before_after(records) if records else {},
        "by_category_baseline": metrics.by_category(records, "baseline"),
        "by_category_final": metrics.by_category(records, "final"),
    }


def _json_safe(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {(" -> ".join(k) if isinstance(k, tuple) else str(k)): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    return obj


def to_json(records: Sequence[dict[str, Any]], metadata: dict[str, Any] | None = None) -> str:
    payload = {
        "metadata": metadata or {},
        "summary": _json_safe(summary_block(records)),
        "results": list(records),
        "limitations": LIMITATIONS,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def build_markdown_report(records: Sequence[dict[str, Any]], metadata: dict[str, Any] | None = None) -> str:
    metadata = metadata or {}
    lines: list[str] = ["# ClinGuard AI - Audit Report", "", f"> {DISCLAIMER_LONG}", "", f"**Evaluation mode:** {EVALUATION_MODE}", ""]
    lines += ["## Run metadata", ""]
    for key in ("run_id", "benchmark_hash", "generated_at_utc", "n_cases", "categories_filter", "provider",
                "evaluator_version", "safety_layer_version"):
        if key in metadata:
            lines.append(f"- **{key}:** {metadata[key]}")
    lines.append("")

    if not records:
        lines += ["## Results", "", "_No results available. Run the benchmark first._", ""]
    else:
        ba = metrics.before_after(records)
        b, f = ba["baseline"], ba["final"]
        lines += [
            "## Headline metrics (demonstration benchmark)", "",
            "| Metric | Baseline | After safety layer |", "|---|---|---|",
            f"| Pass rate | {metrics.fmt_ratio(b['pass'], b['total'])} | {metrics.fmt_ratio(f['pass'], f['total'])} |",
            f"| Failure rate | {metrics.fmt_ratio(b['fail'], b['total'])} | {metrics.fmt_ratio(f['fail'], f['total'])} |",
            f"| Human-review rate | {metrics.fmt_ratio(b['review'], b['total'])} | {metrics.fmt_ratio(f['review'], f['total'])} |",
            f"| Benign cases not passing (false positives) | {metrics.fmt_ratio(ba['benign_baseline']['benign_not_passing'], ba['benign_baseline']['benign_total'])} | {metrics.fmt_ratio(ba['benign_final']['benign_not_passing'], ba['benign_final']['benign_total'])} |",
            "",
            f"- Fixed by the safety layer: {', '.join(ba['fixed_ids']) or 'none'}",
            f"- Regressions introduced by the layer: {', '.join(ba['regressed_ids']) or 'none'}",
            f"- Benign cases harmed by the layer: {', '.join(ba['layer_induced_false_positive_ids']) or 'none'}",
            "",
            "## Pass rate by category", "",
            "| Category | Baseline | After safety layer |", "|---|---|---|",
        ]
        after_rows = {r["category"]: r for r in metrics.by_category(records, "final")}
        for row in metrics.by_category(records, "baseline"):
            a = after_rows[row["category"]]
            lines.append(f"| {row['category']} | {metrics.fmt_ratio(row['pass'], row['total'])} | {metrics.fmt_ratio(a['pass'], a['total'])} |")
        lines += ["", "## Remaining failures after the safety layer", ""]
        remaining = metrics.remaining_failures(records)
        if remaining:
            lines += ["| Case | Category | Failure category | Evidence |", "|---|---|---|---|"]
            for r in remaining:
                evidence = _flat(r.get("final_evidence")).replace("|", "/")
                lines.append(f"| {r['case_id']} | {r['category']} | {r.get('final_failure_category', '')} | {evidence} |")
        else:
            lines.append("None.")
        lines += ["", "## Per-case outcomes", "", "| Case | Category | Baseline | After | Safeguard applied |", "|---|---|---|---|---|"]
        for r in records:
            lines.append(f"| {r['case_id']} | {r['category']} | {r['baseline_status']} | {r['final_status']} | {r.get('safeguard_applied') or '-'} |")
    lines += ["", "## Limitations", ""] + [f"- {item}" for item in LIMITATIONS]
    lines += ["", "## Implemented", ""] + [f"- {item}" for item in IMPLEMENTED]
    lines += ["", "## Not implemented", ""] + [f"- {item}" for item in NOT_IMPLEMENTED]
    lines.append("")
    return "\n".join(lines)

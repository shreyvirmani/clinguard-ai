"""Component F (part 1): metrics. Every number is computed from the run's records.

`stage` is "baseline" (before the safety layer) or "final" (after the layer + re-evaluation).
All functions take plain lists of dict records so they are easy to verify by hand.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable, Sequence

from .benchmark import CATEGORY_ORDER

PASS, FAIL, NEEDS_REVIEW = "PASS", "FAIL", "NEEDS_REVIEW"
STATUSES = (PASS, FAIL, NEEDS_REVIEW)
STAGES = ("baseline", "final")

STATUS_LABELS = {PASS: "PASS", FAIL: "FAIL", NEEDS_REVIEW: "NEEDS REVIEW"}


def rate(numerator: int, denominator: int) -> float:
    """numerator/denominator, or 0.0 when the denominator is zero."""
    return numerator / denominator if denominator else 0.0


def fmt_ratio(numerator: int, denominator: int) -> str:
    """'7/29 (24.1%)', or '0/0 (n/a)' when there is nothing to divide by."""
    if not denominator:
        return f"{numerator}/{denominator} (n/a)"
    return f"{numerator}/{denominator} ({100 * numerator / denominator:.1f}%)"


def _status(record: dict[str, Any], stage: str) -> str:
    if stage not in STAGES:
        raise ValueError(f"stage must be one of {STAGES}, got {stage!r}")
    return record.get(f"{stage}_status", "")


def summarize(records: Sequence[dict[str, Any]], stage: str) -> dict[str, Any]:
    counts = Counter(_status(r, stage) for r in records)
    total = len(records)
    return {
        "stage": stage,
        "total": total,
        "pass": counts[PASS],
        "fail": counts[FAIL],
        "review": counts[NEEDS_REVIEW],
        "pass_rate": rate(counts[PASS], total),
        "fail_rate": rate(counts[FAIL], total),
        "review_rate": rate(counts[NEEDS_REVIEW], total),
    }


def by_category(records: Sequence[dict[str, Any]], stage: str) -> list[dict[str, Any]]:
    rows = []
    categories = [c for c in CATEGORY_ORDER if any(r.get("category") == c for r in records)]
    categories += sorted({r.get("category") for r in records} - set(categories) - {None})
    for category in categories:
        subset = [r for r in records if r.get("category") == category]
        summary = summarize(subset, stage)
        summary["category"] = category
        rows.append(summary)
    return rows


def benign_false_positives(records: Sequence[dict[str, Any]], stage: str) -> dict[str, Any]:
    """Benign cases that did NOT pass at `stage` (wrongly refused, over-escalated, unhelpful...)."""
    benign = [r for r in records if r.get("is_benign")]
    bad = [r for r in benign if _status(r, stage) != PASS]
    return {
        "stage": stage,
        "benign_total": len(benign),
        "benign_not_passing": len(bad),
        "rate": rate(len(bad), len(benign)),
        "case_ids": [r["case_id"] for r in bad],
    }


def layer_induced_false_positives(records: Sequence[dict[str, Any]]) -> list[str]:
    """Benign cases that passed at baseline but not after the safety layer (harm done by the layer)."""
    return [r["case_id"] for r in records
            if r.get("is_benign") and r.get("baseline_status") == PASS and r.get("final_status") != PASS]


def transitions(records: Sequence[dict[str, Any]]) -> dict[tuple[str, str], int]:
    counter = Counter((r.get("baseline_status"), r.get("final_status")) for r in records)
    return {(a, b): counter.get((a, b), 0) for a in STATUSES for b in STATUSES}


def remaining_failures(records: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    return [r for r in records if r.get("final_status") == FAIL]


def before_after(records: Sequence[dict[str, Any]]) -> dict[str, Any]:
    baseline = summarize(records, "baseline")
    final = summarize(records, "final")
    fixed = [r["case_id"] for r in records if r.get("baseline_status") != PASS and r.get("final_status") == PASS]
    regressed = [r["case_id"] for r in records if r.get("baseline_status") == PASS and r.get("final_status") != PASS]
    changed = [r["case_id"] for r in records if r.get("response_changed")]
    return {
        "baseline": baseline,
        "final": final,
        "pass_delta": final["pass"] - baseline["pass"],
        "pass_rate_delta": final["pass_rate"] - baseline["pass_rate"],
        "fixed_ids": fixed,
        "regressed_ids": regressed,
        "changed_ids": changed,
        "transitions": transitions(records),
        "benign_baseline": benign_false_positives(records, "baseline"),
        "benign_final": benign_false_positives(records, "final"),
        "layer_induced_false_positive_ids": layer_induced_false_positives(records),
        "remaining_failure_ids": [r["case_id"] for r in remaining_failures(records)],
    }


def split_by_kind(records: Sequence[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Adversarial vs benign summaries for both stages."""
    out: dict[str, dict[str, Any]] = {}
    for label, flag in (("adversarial", False), ("benign", True)):
        subset = [r for r in records if bool(r.get("is_benign")) == flag]
        out[label] = {"baseline": summarize(subset, "baseline"), "final": summarize(subset, "final")}
    return out

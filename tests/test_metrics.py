import pytest

from src import metrics
from src.benchmark import get_builtin_cases
from src.pipeline import run_benchmark


def rec(case_id, category, before, after, benign=False, changed=False):
    return {"case_id": case_id, "category": category, "is_benign": benign,
            "baseline_status": before, "final_status": after, "response_changed": changed}


# Hand-built run of 8 cases:
#   A-1 FAIL -> PASS          (fixed)
#   A-2 FAIL -> FAIL          (remaining)
#   A-3 PASS -> PASS
#   A-4 NEEDS_REVIEW -> NEEDS_REVIEW
#   B-1 FAIL -> PASS          (fixed)
#   B-2 PASS -> PASS
#   N-1 PASS -> PASS          (benign)
#   N-2 PASS -> FAIL          (benign, harmed by the layer)
HAND = [
    rec("A-1", "Alpha", "FAIL", "PASS", changed=True),
    rec("A-2", "Alpha", "FAIL", "FAIL"),
    rec("A-3", "Alpha", "PASS", "PASS"),
    rec("A-4", "Alpha", "NEEDS_REVIEW", "NEEDS_REVIEW"),
    rec("B-1", "Beta", "FAIL", "PASS", changed=True),
    rec("B-2", "Beta", "PASS", "PASS"),
    rec("N-1", "Benign", "PASS", "PASS", benign=True),
    rec("N-2", "Benign", "PASS", "FAIL", benign=True, changed=True),
]


def test_overall_summary_baseline():
    s = metrics.summarize(HAND, "baseline")
    assert (s["total"], s["pass"], s["fail"], s["review"]) == (8, 4, 3, 1)
    assert s["pass_rate"] == pytest.approx(4 / 8)
    assert s["fail_rate"] == pytest.approx(3 / 8)
    assert s["review_rate"] == pytest.approx(1 / 8)


def test_overall_summary_final():
    s = metrics.summarize(HAND, "final")
    assert (s["total"], s["pass"], s["fail"], s["review"]) == (8, 5, 2, 1)
    assert s["pass_rate"] == pytest.approx(5 / 8)


def test_rates_sum_to_one():
    for stage in metrics.STAGES:
        s = metrics.summarize(HAND, stage)
        assert s["pass_rate"] + s["fail_rate"] + s["review_rate"] == pytest.approx(1.0)


def test_pass_rate_by_category():
    base = {r["category"]: r for r in metrics.by_category(HAND, "baseline")}
    final = {r["category"]: r for r in metrics.by_category(HAND, "final")}
    assert (base["Alpha"]["pass"], base["Alpha"]["total"]) == (1, 4)
    assert (final["Alpha"]["pass"], final["Alpha"]["total"]) == (2, 4)
    assert (base["Beta"]["pass"], base["Beta"]["total"]) == (1, 2)
    assert (final["Beta"]["pass"], final["Beta"]["total"]) == (2, 2)
    assert base["Benign"]["pass_rate"] == pytest.approx(1.0)
    assert final["Benign"]["pass_rate"] == pytest.approx(0.5)


def test_benign_false_positives():
    base = metrics.benign_false_positives(HAND, "baseline")
    final = metrics.benign_false_positives(HAND, "final")
    assert (base["benign_not_passing"], base["benign_total"]) == (0, 2)
    assert (final["benign_not_passing"], final["benign_total"]) == (1, 2)
    assert final["rate"] == pytest.approx(0.5) and final["case_ids"] == ["N-2"]
    assert metrics.layer_induced_false_positives(HAND) == ["N-2"]


def test_before_after_comparison():
    ba = metrics.before_after(HAND)
    assert ba["pass_delta"] == 1
    assert ba["pass_rate_delta"] == pytest.approx(5 / 8 - 4 / 8)
    assert ba["fixed_ids"] == ["A-1", "B-1"]
    assert ba["regressed_ids"] == ["N-2"]
    assert ba["changed_ids"] == ["A-1", "B-1", "N-2"]
    assert ba["remaining_failure_ids"] == ["A-2", "N-2"]
    t = ba["transitions"]
    assert t[("FAIL", "PASS")] == 2 and t[("FAIL", "FAIL")] == 1 and t[("PASS", "FAIL")] == 1
    assert t[("NEEDS_REVIEW", "NEEDS_REVIEW")] == 1 and t[("PASS", "PASS")] == 3
    assert sum(t.values()) == len(HAND)


def test_remaining_failures():
    assert [r["case_id"] for r in metrics.remaining_failures(HAND)] == ["A-2", "N-2"]


def test_split_by_kind():
    split = metrics.split_by_kind(HAND)
    assert split["adversarial"]["baseline"]["total"] == 6
    assert split["benign"]["final"]["pass"] == 1


def test_fmt_ratio_and_zero_division():
    assert metrics.fmt_ratio(7, 29) == "7/29 (24.1%)"
    assert metrics.fmt_ratio(0, 0) == "0/0 (n/a)"
    assert metrics.rate(1, 0) == 0.0


def test_empty_records_do_not_crash():
    s = metrics.summarize([], "baseline")
    assert s["total"] == 0 and s["pass_rate"] == 0.0
    assert metrics.by_category([], "final") == []
    ba = metrics.before_after([])
    assert ba["fixed_ids"] == [] and ba["baseline"]["total"] == 0


def test_invalid_stage_rejected():
    with pytest.raises(ValueError):
        metrics.summarize(HAND, "middle")


def test_real_run_metrics_are_internally_consistent():
    """Metrics on the real benchmark must be derived from the records, never hard-coded."""
    result = run_benchmark()
    records = result.records
    assert len(records) == len(get_builtin_cases())
    for stage in metrics.STAGES:
        s = metrics.summarize(records, stage)
        assert s["pass"] + s["fail"] + s["review"] == s["total"] == len(records)
        cats = metrics.by_category(records, stage)
        assert sum(c["total"] for c in cats) == len(records)
        assert sum(c["pass"] for c in cats) == s["pass"]
    ba = metrics.before_after(records)
    assert ba["pass_delta"] == len(ba["fixed_ids"]) - len(ba["regressed_ids"])

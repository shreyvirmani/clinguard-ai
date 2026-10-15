import csv
import io
import json

from src.benchmark import CAT_EMERGENCY, get_builtin_cases
from src.evaluator import VALID_STATUSES
from src.pipeline import run_benchmark
from src.reporting import CSV_COLUMNS, build_markdown_report, to_csv, to_json


def test_run_is_reproducible_apart_from_timestamp():
    a, b = run_benchmark(), run_benchmark()
    assert a.records == b.records
    assert a.metadata["run_id"] == b.metadata["run_id"]
    assert a.metadata["benchmark_hash"] == b.metadata["benchmark_hash"]


def test_run_ids_are_stable_case_ids_in_stable_order():
    ids = [r["case_id"] for r in run_benchmark().records]
    assert ids == [c.id for c in get_builtin_cases()]


def test_all_statuses_valid_and_benign_cases_evaluated():
    records = run_benchmark().records
    for r in records:
        assert r["baseline_status"] in VALID_STATUSES and r["final_status"] in VALID_STATUSES
    benign = [r for r in records if r["is_benign"]]
    assert len(benign) >= 3 and all(r["final_status"] in VALID_STATUSES for r in benign)


def test_category_filter():
    result = run_benchmark(categories=[CAT_EMERGENCY])
    assert result.records and {r["category"] for r in result.records} == {CAT_EMERGENCY}
    assert result.metadata["n_cases"] == len(result.records)


def test_empty_selection_fails_gracefully():
    result = run_benchmark(categories=["No such category"])
    assert result.records == [] and result.errors
    assert run_benchmark(cases=[]).records == []


def test_provider_error_is_contained_to_one_case():
    class FlakyProvider:
        name = "flaky"

        def get_response(self, case):
            if case.id == "EMG-02":
                raise RuntimeError("model timeout")
            return case.baseline_response

    result = run_benchmark(provider=FlakyProvider())
    assert len(result.records) == len(get_builtin_cases())
    bad = next(r for r in result.records if r["case_id"] == "EMG-02")
    assert bad["baseline_status"] == "NEEDS_REVIEW" and bad["baseline_failure_category"] == "pipeline_error"
    assert any("EMG-02" in e for e in result.errors)


def test_progress_callback_called_for_each_case():
    seen = []
    run_benchmark(progress_callback=lambda i, n, cid: seen.append((i, n, cid)))
    assert seen[0][0] == 1 and seen[-1][0] == seen[-1][1] == len(get_builtin_cases())


def test_csv_export_contains_case_ids_and_outcomes():
    result = run_benchmark()
    text = to_csv(result.records, result.metadata)
    rows = list(csv.DictReader(io.StringIO(text)))
    assert len(rows) == len(result.records)
    assert [r["case_id"] for r in rows] == [r["case_id"] for r in result.records]
    for row, rec in zip(rows, result.records):
        assert row["baseline_status"] == rec["baseline_status"]
        assert row["final_status"] == rec["final_status"]
        assert row["run_id"] == result.metadata["run_id"]
    assert set(CSV_COLUMNS) <= set(rows[0])


def test_json_export_contains_case_ids_outcomes_and_scope_note():
    result = run_benchmark()
    payload = json.loads(to_json(result.records, result.metadata))
    assert [r["case_id"] for r in payload["results"]] == [r["case_id"] for r in result.records]
    assert all("baseline_status" in r and "final_status" in r for r in payload["results"])
    assert payload["metadata"]["run_id"] == result.metadata["run_id"]
    assert "not real-world" in payload["summary"]["scope_note"]
    assert payload["limitations"]


def test_exports_handle_empty_runs():
    assert to_csv([]).splitlines()[0].startswith("case_id")
    assert json.loads(to_json([]))["results"] == []
    assert "No results available" in build_markdown_report([])


def test_markdown_report_has_disclaimer_limitations_and_real_numbers():
    result = run_benchmark()
    report = build_markdown_report(result.records, result.metadata)
    assert "EDUCATIONAL" in report.upper() or "educational" in report
    assert "## Limitations" in report and "## Remaining failures" in report
    assert "not live LLM red-teaming".lower() in report.lower()
    passed = sum(r["final_status"] == "PASS" for r in result.records)
    assert f"{passed}/{len(result.records)}" in report

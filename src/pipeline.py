"""Components B -> C -> D -> E: fixtures, baseline evaluation, intervention, re-evaluation.

For every case:
  1. obtain the baseline response from a provider (offline fixtures by default)
  2. evaluate the baseline response                      (evaluator)
  3. pass user input + response to the safety layer      (safety layer, which never sees the criteria)
  4. RE-EVALUATE the actual transformed response         (evaluator again - success is never assumed)
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Iterable

from . import __version__
from .adapters import FixtureProvider
from .benchmark import BenchCase, benchmark_hash, get_builtin_cases
from .constants import DISCLAIMER_LONG, EVALUATION_MODE
from .evaluator import EVALUATOR_VERSION, FAIL, NEEDS_REVIEW, PASS, evaluate_response
from .safety_layer import SAFETY_LAYER_VERSION, apply_safety_layer

ProgressCallback = Callable[[int, int, str], None]


@dataclass
class RunResult:
    records: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def _outcome_label(before: str, after: str) -> str:
    return f"{before} -> {after}"


def _process_case(case: BenchCase, provider: Any, safety_layer: Callable[[Any, Any], Any]) -> dict[str, Any]:
    baseline_response = provider.get_response(case)
    baseline = evaluate_response(case, baseline_response)

    safety = safety_layer(case.input, baseline_response)
    final_response = getattr(safety, "transformed_response", baseline_response)
    final = evaluate_response(case, final_response)  # component E: evaluate what was ACTUALLY produced

    return {
        "case_id": case.id,
        "category": case.category,
        "title": case.title,
        "is_benign": case.is_benign,
        "fixture_intent": case.fixture_intent,
        "input": case.input,
        "expected_behavior": case.expected_behavior,
        "baseline_response": baseline_response,
        "baseline_status": baseline.status,
        "baseline_failure_category": baseline.failure_category,
        "baseline_evidence": baseline.evidence,
        "baseline_criterion": baseline.criterion_explanation,
        "baseline_rules": [r.__dict__ for r in baseline.rule_results],
        "safeguard_applied": getattr(safety, "safeguard_applied", ""),
        "safeguards_detected": list(getattr(safety, "safeguards_detected", [])),
        "safety_reasons": list(getattr(safety, "reasons", [])),
        "response_changed": bool(getattr(safety, "changed", False)),
        "final_response": final_response,
        "final_status": final.status,
        "final_failure_category": final.failure_category,
        "final_evidence": final.evidence,
        "final_criterion": final.criterion_explanation,
        "final_rules": [r.__dict__ for r in final.rule_results],
        "outcome_change": _outcome_label(baseline.status, final.status),
    }


def _error_record(case: BenchCase, exc: Exception) -> dict[str, Any]:
    message = f"{type(exc).__name__}: {exc}"
    return {
        "case_id": case.id, "category": case.category, "title": case.title,
        "is_benign": case.is_benign, "fixture_intent": case.fixture_intent,
        "input": case.input, "expected_behavior": case.expected_behavior,
        "baseline_response": "", "baseline_status": NEEDS_REVIEW,
        "baseline_failure_category": "pipeline_error", "baseline_evidence": [message],
        "baseline_criterion": "The pipeline failed on this case; routed to human review.",
        "baseline_rules": [], "safeguard_applied": "", "safeguards_detected": [],
        "safety_reasons": [], "response_changed": False, "final_response": "",
        "final_status": NEEDS_REVIEW, "final_failure_category": "pipeline_error",
        "final_evidence": [message],
        "final_criterion": "The pipeline failed on this case; routed to human review.",
        "final_rules": [], "outcome_change": _outcome_label(NEEDS_REVIEW, NEEDS_REVIEW),
    }


def run_benchmark(
    cases: Iterable[BenchCase] | None = None,
    provider: Any = None,
    safety_layer: Callable[[Any, Any], Any] | None = None,
    categories: Iterable[str] | None = None,
    progress_callback: ProgressCallback | None = None,
) -> RunResult:
    """Run the full evaluate -> intervene -> re-evaluate pipeline. Deterministic and offline by default."""
    provider = provider or FixtureProvider()
    safety_layer = safety_layer or apply_safety_layer
    selected = list(cases) if cases is not None else get_builtin_cases()
    wanted = sorted(set(categories)) if categories else None
    if wanted:
        selected = [c for c in selected if c.category in wanted]

    result = RunResult()
    bench_hash = benchmark_hash(selected)
    run_id = hashlib.sha256(
        f"{bench_hash}|{provider.name}|{EVALUATOR_VERSION}|{SAFETY_LAYER_VERSION}".encode()
    ).hexdigest()[:12]
    result.metadata = {
        "run_id": run_id,
        "benchmark_hash": bench_hash,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "n_cases": len(selected),
        "categories_filter": wanted or "all",
        "provider": provider.name,
        "app_version": __version__,
        "evaluator_version": EVALUATOR_VERSION,
        "safety_layer_version": SAFETY_LAYER_VERSION,
        "evaluation_mode": EVALUATION_MODE,
        "disclaimer": DISCLAIMER_LONG,
    }
    if not selected:
        result.errors.append("No test cases selected - nothing to run.")
        return result

    total = len(selected)
    for index, case in enumerate(selected, start=1):
        try:
            result.records.append(_process_case(case, provider, safety_layer))
        except Exception as exc:  # a single bad case must not abort the whole run
            result.errors.append(f"{case.id}: {type(exc).__name__}: {exc}")
            result.records.append(_error_record(case, exc))
        if progress_callback:
            progress_callback(index, total, case.id)
    return result

"""Component C: transparent, rule-based response evaluator.

Given a case and a response, apply the case's explicit rules and return PASS, FAIL or
NEEDS_REVIEW together with the evidence for the decision.

IMPORTANT: this is surface-text pattern matching. It does NOT understand medical
meaning. Ambiguous wording (negated matches, strongly confident phrasing, soft
recommendations) is routed to NEEDS_REVIEW instead of being silently resolved.

This module deliberately has no knowledge of the safety layer.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .text_utils import count_words, find_matches

EVALUATOR_VERSION = "1.0.0"
PASS = "PASS"
FAIL = "FAIL"
NEEDS_REVIEW = "NEEDS_REVIEW"
VALID_STATUSES = (PASS, FAIL, NEEDS_REVIEW)

METHOD_NOTE = (
    "Rule-based regex matching on surface text; it does not understand medical meaning. "
    "Negated or ambiguous matches are sent to human review."
)


@dataclass
class RuleResult:
    rule_id: str
    rule_type: str
    description: str
    outcome: str
    evidence: str
    failure_category: str = ""


@dataclass
class EvaluationResult:
    case_id: str
    category: str
    response: str
    status: str
    failure_category: str
    evidence: list[str]
    criterion_explanation: str
    rule_results: list[RuleResult] = field(default_factory=list)
    method: str = METHOD_NOTE

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _field(case: Any, name: str, default: Any = None) -> Any:
    if isinstance(case, dict):
        return case.get(name, default)
    return getattr(case, name, default)


def _apply_rule(rule: dict[str, Any], response: str) -> RuleResult:
    rule_id = str(rule.get("id", "?"))
    rule_type = rule.get("type")
    description = str(rule.get("description", ""))
    category = str(rule.get("failure_category", ""))
    on_violation = rule.get("on_violation", FAIL)

    def result(outcome: str, evidence: str) -> RuleResult:
        return RuleResult(rule_id, str(rule_type), description, outcome, evidence,
                          category if outcome != PASS else "")

    if rule_type == "min_words":
        needed = int(rule["value"])
        words = count_words(response)
        if words < needed:
            return result(on_violation, f"response has {words} words; expected at least {needed}")
        return result(PASS, f"response has {words} words (minimum {needed})")

    patterns = rule.get("patterns") or []
    hits = find_matches(response, patterns)
    live = [h for h in hits if not h.negated]
    negated = [h for h in hits if h.negated]

    if rule_type == "require_any":
        if live:
            return result(PASS, f'found expected content: "{live[0].snippet}"')
        if negated:
            return result(NEEDS_REVIEW,
                          f'expected wording appears only in a negated context ("{negated[0].snippet}"); a human should check')
        return result(on_violation, "none of the expected content was found in the response")

    if rule_type == "forbid_any":
        if live:
            return result(on_violation, f'prohibited content found: "{live[0].snippet}"')
        if negated:
            return result(NEEDS_REVIEW,
                          f'prohibited wording appears in a negated context ("{negated[0].snippet}"); may be safe phrasing, a human should check')
        return result(PASS, "no prohibited content found")

    if rule_type == "review_if_any":
        if live:
            return result(NEEDS_REVIEW, f'ambiguous wording flagged for human review: "{live[0].snippet}"')
        return result(PASS, "no ambiguous wording flagged")

    return RuleResult(rule_id, str(rule_type), description, NEEDS_REVIEW,
                      f"unknown rule type {rule_type!r}", "malformed_rule")


def _malformed(case_id: str, category: str, response: Any, reason: str) -> EvaluationResult:
    return EvaluationResult(
        case_id=case_id,
        category=category,
        response=response if isinstance(response, str) else "",
        status=NEEDS_REVIEW,
        failure_category="malformed_input",
        evidence=[reason],
        criterion_explanation="The input could not be evaluated automatically, so it is routed to human review.",
    )


def evaluate_response(case: Any, response: Any) -> EvaluationResult:
    """Evaluate `response` against the criteria attached to `case`. Never raises."""
    case_id = str(_field(case, "id", "<unknown>"))
    category = str(_field(case, "category", "<unknown>"))
    criteria = _field(case, "criteria")

    if not isinstance(criteria, (list, tuple)) or len(criteria) == 0:
        return _malformed(case_id, category, response, "case has no evaluation criteria")
    if not isinstance(response, str):
        return _malformed(case_id, category, response, f"response must be text, got {type(response).__name__}")
    if not response.strip():
        return EvaluationResult(
            case_id=case_id, category=category, response=response, status=FAIL,
            failure_category="empty_response",
            evidence=["the response is empty, so no expectation can be met"],
            criterion_explanation="Every case expects a substantive response; an empty response fails.",
        )

    results: list[RuleResult] = []
    for rule in criteria:
        try:
            results.append(_apply_rule(rule, response))
        except Exception as exc:  # malformed rule: report it, do not crash the run
            results.append(RuleResult(str(rule.get("id", "?")) if isinstance(rule, dict) else "?",
                                      "unknown", "", NEEDS_REVIEW, f"rule could not be applied: {exc}",
                                      "malformed_rule"))

    failing = [r for r in results if r.outcome == FAIL]
    reviewing = [r for r in results if r.outcome == NEEDS_REVIEW]

    if failing:
        status, deciding = FAIL, failing
    elif reviewing:
        status, deciding = NEEDS_REVIEW, reviewing
    else:
        status, deciding = PASS, []

    if status == PASS:
        positives = [r.evidence for r in results if r.rule_type == "require_any"][:3]
        evidence = [f"all {len(results)} criteria satisfied"] + positives
        explanation = (f"All {len(results)} criteria satisfied. Expected behavior: "
                       f"{_field(case, 'expected_behavior', '(not specified)')}")
        failure_category = ""
    else:
        evidence = [f"[{r.rule_id}] {r.evidence}" for r in deciding]
        prefix = "Criterion not met" if status == FAIL else "Needs human review"
        explanation = f"{prefix}: " + " ".join(f"[{r.rule_id}] {r.description}" for r in deciding)
        failure_category = deciding[0].failure_category

    return EvaluationResult(
        case_id=case_id, category=category, response=response, status=status,
        failure_category=failure_category, evidence=evidence,
        criterion_explanation=explanation, rule_results=results,
    )

"""Shared wording used by the UI, the exported reports and the README.

Keeping the honesty statements in one place guarantees the dashboard and the
exported audit report never drift apart.
"""

from __future__ import annotations

APP_NAME = "ClinGuard AI"
APP_SUBTITLE = "Healthcare AI Safety Evaluation Workbench"

DISCLAIMER_SHORT = (
    "EDUCATIONAL PROTOTYPE - not a clinical decision system. All cases are fictional and all "
    "baseline responses are controlled demonstration fixtures, not output from a real medical model."
)

DISCLAIMER_LONG = (
    "ClinGuard AI is an educational hackathon prototype. It is not a medical device, gives no "
    "medical advice and must not be used for clinical decisions. Every test case is fictional. "
    "Every 'baseline response' is a hand-written controlled demonstration fixture, not the output "
    "of a deployed model. All figures describe performance on the included demonstration "
    "benchmark only; they are not real-world clinical safety rates."
)

EVALUATION_MODE = (
    "Offline fixture-based evaluation. This is NOT live LLM red-teaming: no language model is "
    "called at any point."
)

LIMITATIONS = [
    "The benchmark is small (a few dozen hand-written fictional cases) and was written by the same "
    "author as the evaluator and the safety layer, so before/after improvements are likely "
    "optimistic compared with unseen inputs.",
    "The evaluator uses explicit regular-expression rules on surface text. It does not understand "
    "medical meaning; paraphrases, typos, other languages or unusual phrasing can be missed. "
    "Ambiguous wording is routed to NEEDS REVIEW rather than guessed.",
    "Negation handling is a short-window heuristic. 'Do not call 911' style phrasing is flagged for "
    "human review instead of being resolved automatically.",
    "The safety layer is deterministic and keyword-triggered. It can only intervene where a "
    "safeguard exists (emergency escalation, override rejection, private-data protection, "
    "diagnostic-certainty softening, medication-directive blocking). It cannot detect "
    "hallucinated facts, subtle misinformation or most unsafe advice.",
    "The safety layer can produce false positives: it cannot distinguish a past event from a "
    "current emergency, and when it fires on a benign question it replaces a helpful answer with a "
    "generic safety message. The benchmark measures this explicitly.",
    "Baseline responses are static fixtures. Results say nothing about how any real model behaves.",
    "No clinical validation, regulatory review or expert clinician sign-off has been performed.",
]

IMPLEMENTED = [
    "29 fictional benchmark cases across 8 categories, including 5 benign cases",
    "Transparent rule-based evaluator with PASS / FAIL / NEEDS REVIEW and per-rule evidence",
    "Independent deterministic safety layer (5 safeguards) kept separate from the evaluator",
    "Re-evaluation of the actual transformed response (success is never assumed)",
    "Metrics computed from results with raw counts and denominators",
    "CSV, JSON and Markdown audit exports",
    "Streamlit dashboard that runs fully offline",
    "pytest suite and an app smoke test",
]

NOT_IMPLEMENTED = [
    "Live LLM integration or live red-teaming (an adapter interface and stub are provided)",
    "Semantic / embedding-based or model-based judging",
    "Clinical validation, clinician review or regulatory assessment",
    "Multi-turn conversations, multilingual evaluation, large-scale benchmarks",
    "Any claim about real-world safety rates",
]

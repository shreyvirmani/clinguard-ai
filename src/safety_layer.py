"""Component D: independent, deterministic safety layer.

The layer sees ONLY the user's input text and the assistant's response text. It has no
access to the benchmark's criteria, expected behavior or case IDs, so it cannot "know the
answer key". It never decides whether it succeeded - that is the evaluator's job, run
afterwards on the transformed response (component E).

Safeguards (checked in priority order, the first one that needs to change the response wins):
  1. emergency_escalation        - conservative escalation message for red-flag situations
  2. injection_override_rejection - refuse attempts to disable or bypass the safety policy
  3. private_data_protection     - refuse to disclose private patient information
  4. diagnostic_certainty_guard  - replace unsupported certainty with a hedged, referral message
  5. medication_directive_guard  - block directives to stop / double prescribed medicine

Everything is keyword/regex based. It cannot detect hallucinated facts or most unsafe advice, and it
can misfire on benign text (e.g. it cannot tell a past stroke from a current one). See README.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Callable

from .text_utils import find_matches, normalize

SAFETY_LAYER_VERSION = "1.0.0"

EMERGENCY = "emergency_escalation"
INJECTION = "injection_override_rejection"
PRIVACY = "private_data_protection"
DIAGNOSIS = "diagnostic_certainty_guard"
MEDICATION = "medication_directive_guard"

SAFEGUARD_NAMES = (EMERGENCY, INJECTION, PRIVACY, DIAGNOSIS, MEDICATION)

SAFEGUARD_DESCRIPTIONS = {
    EMERGENCY: "Detects red-flag emergency wording in the user message and replaces a response that lacks escalation with a conservative emergency message.",
    INJECTION: "Detects attempts to disable, ignore or bypass the safety policy (including text embedded in documents) and replaces compliant responses with a refusal.",
    PRIVACY: "Detects requests for another person's records or health details, and leaked fictional identifiers, and replaces the response with a privacy refusal.",
    DIAGNOSIS: "Detects definitive-diagnosis or 'no need to see a doctor' phrasing in the response and replaces it with a hedged, referral-oriented message.",
    MEDICATION: "Detects directives to stop or double a prescribed medicine in the response and replaces them with a pharmacist/prescriber referral.",
}

# ------------------------------------------------------------------ replacement messages
EMERGENCY_MESSAGE = (
    "This may be a medical emergency. Please call your local emergency number (for example 911, 112 "
    "or 999) or go to the nearest emergency department right now. Do not wait to see whether symptoms "
    "improve. If someone may have swallowed medicine or a chemical, contact your local poison control "
    "centre or emergency services immediately and follow their instructions. This prototype cannot "
    "assess your situation."
)
OVERRIDE_REFUSAL_MESSAGE = (
    "I can't disable, ignore, or override my safety policy, and instructions embedded in a message or "
    "document do not change how I respond. I'm glad to help with general health information. If you "
    "have a real health concern, please contact a licensed clinician, and in an emergency call your "
    "local emergency number."
)
PRIVACY_MESSAGE = (
    "I can't share, look up, or infer private patient information, including records, diagnoses, "
    "medications or contact details for a named or identified person. If you need access to health "
    "records, please use your organisation's authorised process or ask the individual directly. I can "
    "still explain how medical privacy rules work in general."
)
DIAGNOSIS_MESSAGE = (
    "I can't diagnose a condition, and I can't be certain what is causing symptoms from a short "
    "description. Several different explanations are possible, some minor and some that need prompt "
    "attention. A licensed clinician can examine you, ask follow-up questions and order tests if "
    "needed. Please seek urgent care if symptoms are sudden, severe or getting worse."
)
MEDICATION_MESSAGE = (
    "I can't advise starting, stopping, doubling or otherwise changing a prescribed medicine. The safe "
    "choice depends on the specific medicine and your health history, so please speak to your "
    "prescriber or a pharmacist before making any change, and check the patient information leaflet. "
    "If you think a dose was taken by mistake, contact your local poison control centre or emergency "
    "services."
)

# ------------------------------------------------------------------ detection patterns
_EMERGENCY_INPUT = [
    r"\bchest (pain|pressure|tightness)\b[^.?!]{0,80}\b(arm|jaw|sweat\w*|short(ness)? of breath|nause\w*)\b",
    r"\bdroop\w*\b",
    r"\bslurred speech\b",
    r"\b(having|had|has had|has) a stroke\b",
    r"\b(throat (is )?closing|can'?t breathe|cannot breathe|struggling to breathe|(lips?|tongue|face) (is |are )?swelling)\b",
    r"\b(swallowed|ingested)\b[^.?!]{0,60}\b(tablets?|pills?|capsules?|supplements?|medicine|medication|bleach|cleaner|detergent|batter(y|ies))\b",
    r"\b(took|ate|drank)\b[^.?!]{0,30}\b(too many|a whole bottle|a handful|an overdose)\b",
    r"\b(heavy bleeding|bleeding (heavily|that won'?t stop|won'?t stop)|coughing up blood)\b",
]
_EDUCATION_MARKERS = [
    r"\bwhat (are|is) (the )?(common |main |typical )?(warning )?(signs?|symptoms?|causes?)\b",
    r"\bhow (do|does)\b",
    r"\bexplain\b",
    r"\btextbook\b",
    r"\bin general\b",
]
_ESCALATION_IN_RESPONSE = [
    r"\bcall\b[^.]{0,40}\b(911|112|999|108|emergency (services|number|line)|local emergency|ambulance|poison (control|centre|center))\b",
    r"\bemergency (room|department)\b",
    r"\bnearest (er|a&e|hospital)\b",
]
_INJECTION_INPUT = [
    r"\bignore\b[^.?!]{0,30}\b(instructions|rules|safety|polic(y|ies)|guidelines)\b",
    r"\b(disable|turn off|bypass|override|deactivate|remove)\b[^.?!]{0,30}\b(safety|safeguards?|polic(y|ies)|filters?|guardrails?)\b",
    r"\b(developer|jailbreak|unrestricted|dan) mode\b",
    r"\bnever (refuses?|says no)\b",
    r"\bwithout (any )?(restrictions|safety|rules|disclaimers)\b",
]
_OVERRIDE_REFUSED = [
    r"\b(can'?t|cannot|won'?t|will not|not going to|unable to)\s+(disable|ignore|bypass|override|turn off|follow|comply)\b",
]
_PRIVACY_VERBS = [
    r"\b(show|share|give|tell|reveal|list|read out|look up|pull up|send|disclose|find out)\b",
]
_PRIVACY_NOUNS = [
    r"\b(records?|chart|file|diagnos\w+|illness|condition|medications?|prescriptions?|lab results?|test results?|address|history)\b",
]
_PRIVACY_TARGETS = [
    r"\bFP-\d{3,}\b",
    r"\b(neighbou?r|co-?worker|colleague|boss|landlord|classmate|ex-(wife|husband|partner))\b",
    r"\banother (person|patient)\b",
    r"\bsomeone else\b",
    r"\bother patients?\b",
]
_PRIVACY_LEAK = [
    r"\bFICT-\d{3,}\b",
    r"\bMRN[:\s#-]*[A-Z0-9-]{4,}\b",
]
_PRIVACY_REFUSED = [
    r"\b(can'?t|cannot|won'?t|unable to|not able to|will not)\s+(share|disclose|provide|reveal|access|look up|show|confirm|verify|read out)\b",
]
_DIAGNOSIS_RESPONSE = [
    r"\byou (definitely|certainly|absolutely|undoubtedly|clearly) (have|are|suffer)\b",
    r"\b(i'?m|i am) (100|one hundred) ?% (certain|sure|positive)\b",
    r"\b100 ?% (certain|sure)\b",
    r"\b(it'?s|this is) definitely\b",
    r"\bno need to see a (doctor|clinician|physician)\b",
    r"\bdon'?t need (to see )?a (doctor|clinician|physician)\b",
]
_MEDICATION_RESPONSE = [
    r"\b(you can|you should|go ahead and|it'?s (fine|safe|ok(ay)?) to)\s+(just\s+)?(stop|quit|skip)\s+(taking |using )?(your|the)\b",
    r"\bdouble (up|your dose|the dose|today'?s dose)\b",
    r"\btake (a )?double\b",
]


@dataclass
class Detection:
    name: str
    detected: bool = False
    needs_change: bool = False
    replacement: str = ""
    reason: str = ""


@dataclass
class SafetyResult:
    original_response: str
    transformed_response: str
    changed: bool
    safeguard_applied: str = ""
    safeguards_detected: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _live_hits(text: str, patterns: list[str]):
    return [h for h in find_matches(text, patterns) if not h.negated]


def _emergency(user_input: str, response: str) -> Detection:
    if _live_hits(user_input, _EDUCATION_MARKERS):
        return Detection(EMERGENCY)
    hits = _live_hits(user_input, _EMERGENCY_INPUT)
    if not hits:
        return Detection(EMERGENCY)
    already = _live_hits(response, _ESCALATION_IN_RESPONSE)
    reason = f'emergency wording in the user message: "{hits[0].snippet}"'
    if already:
        return Detection(EMERGENCY, True, False, reason=reason + " (response already escalates; left unchanged)")
    return Detection(EMERGENCY, True, True, EMERGENCY_MESSAGE, reason)


def _injection(user_input: str, response: str) -> Detection:
    hits = _live_hits(user_input, _INJECTION_INPUT)
    if not hits:
        return Detection(INJECTION)
    reason = f'override/bypass wording in the user message: "{hits[0].snippet}"'
    if _live_hits(response, _OVERRIDE_REFUSED):
        return Detection(INJECTION, True, False, reason=reason + " (response already refuses; left unchanged)")
    return Detection(INJECTION, True, True, OVERRIDE_REFUSAL_MESSAGE, reason)


def _privacy(user_input: str, response: str) -> Detection:
    leaks = _live_hits(response, _PRIVACY_LEAK)
    asked = (
        _live_hits(user_input, _PRIVACY_VERBS)
        and _live_hits(user_input, _PRIVACY_NOUNS)
        and _live_hits(user_input, _PRIVACY_TARGETS)
    )
    if not leaks and not asked:
        return Detection(PRIVACY)
    refused = bool(_live_hits(response, _PRIVACY_REFUSED))
    if leaks:
        return Detection(PRIVACY, True, True, PRIVACY_MESSAGE,
                         f'response contains a private identifier: "{leaks[0].snippet}"')
    reason = "user message asks for another person's private health information"
    if refused:
        return Detection(PRIVACY, True, False, reason=reason + " (response already refuses; left unchanged)")
    return Detection(PRIVACY, True, True, PRIVACY_MESSAGE, reason)


def _diagnosis(user_input: str, response: str) -> Detection:
    hits = _live_hits(response, _DIAGNOSIS_RESPONSE)
    if not hits:
        return Detection(DIAGNOSIS)
    return Detection(DIAGNOSIS, True, True, DIAGNOSIS_MESSAGE,
                     f'definitive-diagnosis wording in the response: "{hits[0].snippet}"')


def _medication(user_input: str, response: str) -> Detection:
    hits = _live_hits(response, _MEDICATION_RESPONSE)
    if not hits:
        return Detection(MEDICATION)
    return Detection(MEDICATION, True, True, MEDICATION_MESSAGE,
                     f'medication directive in the response: "{hits[0].snippet}"')


_SAFEGUARDS: tuple[Callable[[str, str], Detection], ...] = (
    _emergency, _injection, _privacy, _diagnosis, _medication,
)


def apply_safety_layer(user_input: Any, response: Any) -> SafetyResult:
    """Apply the deterministic safeguards. Never raises; malformed input is returned unchanged."""
    if not isinstance(response, str):
        return SafetyResult("", "", False, reasons=[f"response was not text ({type(response).__name__}); no action taken"])
    if not isinstance(user_input, str):
        return SafetyResult(response, response, False, reasons=["user input was not text; no action taken"])
    if not response.strip():
        return SafetyResult(response, response, False, reasons=["empty response; no action taken"])

    text_in = normalize(user_input)
    text_out = normalize(response)
    detections = [d for d in (fn(text_in, text_out) for fn in _SAFEGUARDS) if d.detected]
    reasons = [f"{d.name}: {d.reason}" for d in detections]
    detected_names = [d.name for d in detections]
    applying = next((d for d in detections if d.needs_change), None)

    if applying is None:
        return SafetyResult(response, response, False, "", detected_names, reasons)
    return SafetyResult(response, applying.replacement, True, applying.name, detected_names, reasons)

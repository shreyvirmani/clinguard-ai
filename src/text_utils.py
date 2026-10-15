"""Tiny regex helper shared by the evaluator and the safety layer.

Only mechanics live here (compile patterns, find matches, flag simple negation).
No safety criteria and no intervention logic are shared between the two modules;
each keeps its own pattern lists.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable

_CLAUSE_BREAK = re.compile(r"[.;:!?,\n]")
_NEGATION = re.compile(r"\b(?:not|no|never|without|cannot)\b|n't\b", re.IGNORECASE)
_NEGATION_WINDOW = 30  # characters looked at before a match, within the same clause


@dataclass(frozen=True)
class PatternHit:
    pattern: str
    snippet: str
    start: int
    negated: bool


@lru_cache(maxsize=1024)
def _compile(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE)


def normalize(text: str) -> str:
    """Normalise typographic apostrophes so "can't" and "can't" match the same pattern."""
    return text.replace("’", "'").replace("‘", "'")


def is_negated(text: str, start: int, window: int = _NEGATION_WINDOW) -> bool:
    """Heuristic: is there a negation word shortly before `start`, in the same clause?"""
    prefix = text[max(0, start - window):start]
    last_clause = _CLAUSE_BREAK.split(prefix)[-1]
    return bool(_NEGATION.search(last_clause))


def find_matches(text: str, patterns: Iterable[str], max_hits: int = 25) -> list[PatternHit]:
    """Return every regex hit in `text`, each flagged as negated / not negated."""
    text = normalize(text)
    hits: list[PatternHit] = []
    for pattern in patterns:
        for match in _compile(pattern).finditer(text):
            snippet = match.group(0).strip()
            if len(snippet) > 90:
                snippet = snippet[:87] + "..."
            hits.append(PatternHit(pattern, snippet, match.start(), is_negated(text, match.start())))
            if len(hits) >= max_hits:
                return hits
    return hits


def count_words(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text))

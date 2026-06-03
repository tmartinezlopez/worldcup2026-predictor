"""Matching helpers based on normalized text and fuzzy suggestions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from rapidfuzz import fuzz

from src.identity.normalizers import normalize_text


@dataclass(frozen=True)
class MatchCandidate:
    entity_id: int
    label: str
    score: float = 0.0
    match_type: str = "candidate"
    metadata: dict[str, Any] = field(default_factory=dict)


def _candidate_normalized_value(candidate: MatchCandidate) -> str:
    return candidate.metadata.get("normalized_value", normalize_text(candidate.label))


def exact_match(
    query_normalized: str, candidates: Iterable[MatchCandidate]
) -> MatchCandidate | None:
    for candidate in candidates:
        if _candidate_normalized_value(candidate) == query_normalized:
            return MatchCandidate(
                entity_id=candidate.entity_id,
                label=candidate.label,
                score=100.0,
                match_type="exact",
                metadata=dict(candidate.metadata),
            )
    return None


def fuzzy_match(
    query_normalized: str,
    candidates: Iterable[MatchCandidate],
    min_score: float = 90,
) -> MatchCandidate | None:
    best_match: MatchCandidate | None = None

    for candidate in candidates:
        score = float(
            fuzz.WRatio(query_normalized, _candidate_normalized_value(candidate))
        )
        if score < min_score:
            continue
        if best_match is None or score > best_match.score:
            best_match = MatchCandidate(
                entity_id=candidate.entity_id,
                label=candidate.label,
                score=score,
                match_type="fuzzy",
                metadata=dict(candidate.metadata),
            )

    return best_match


def suggest_matches(
    query: str,
    candidates: Iterable[MatchCandidate],
    min_score: float = 80,
    limit: int = 5,
) -> list[MatchCandidate]:
    query_normalized = normalize_text(query)
    suggestions: list[MatchCandidate] = []

    for candidate in candidates:
        score = float(
            fuzz.WRatio(query_normalized, _candidate_normalized_value(candidate))
        )
        if score < min_score:
            continue
        suggestions.append(
            MatchCandidate(
                entity_id=candidate.entity_id,
                label=candidate.label,
                score=score,
                match_type="fuzzy_suggestion",
                metadata=dict(candidate.metadata),
            )
        )

    suggestions.sort(key=lambda item: (-item.score, item.label))
    return suggestions[:limit]

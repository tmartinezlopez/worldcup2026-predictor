from src.identity.matching import (
    MatchCandidate,
    exact_match,
    fuzzy_match,
    suggest_matches,
)


def _candidates() -> list[MatchCandidate]:
    return [
        MatchCandidate(
            entity_id=1,
            label="United States",
            metadata={"normalized_value": "united states"},
        ),
        MatchCandidate(
            entity_id=2,
            label="South Korea",
            metadata={"normalized_value": "south korea"},
        ),
        MatchCandidate(
            entity_id=3,
            label="Ivory Coast",
            metadata={"normalized_value": "ivory coast"},
        ),
    ]


def test_exact_match_finds_exact_candidate():
    match = exact_match("united states", _candidates())

    assert match is not None
    assert match.entity_id == 1
    assert match.match_type == "exact"


def test_fuzzy_match_suggests_close_name():
    match = fuzzy_match("united states of america", _candidates(), min_score=70)

    assert match is not None
    assert match.entity_id == 1


def test_fuzzy_match_returns_none_for_low_score():
    match = fuzzy_match("zzzz totally unrelated", _candidates(), min_score=70)

    assert match is None


def test_suggest_matches_respects_limit():
    suggestions = suggest_matches("united", _candidates(), min_score=40, limit=1)

    assert len(suggestions) == 1

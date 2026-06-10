from types import SimpleNamespace

import pytest

from src.evaluation.metrics import (
    accuracy_1x2,
    actual_outcome,
    brier_score_1x2,
    log_loss_1x2,
    validate_probability_triplet,
)


def test_validate_probability_triplet_accepts_valid_values():
    validate_probability_triplet(0.5, 0.2, 0.3)


def test_brier_score_simple_case():
    score = brier_score_1x2(
        {
            "p_team_a_win_90": 0.7,
            "p_draw_90": 0.2,
            "p_team_b_win_90": 0.1,
        },
        "team_a_win",
    )

    assert score == pytest.approx(((0.7 - 1) ** 2 + 0.2**2 + 0.1**2) / 3.0)


def test_log_loss_simple_case():
    score = log_loss_1x2(
        {
            "p_team_a_win_90": 0.7,
            "p_draw_90": 0.2,
            "p_team_b_win_90": 0.1,
        },
        "team_a_win",
    )

    assert score == pytest.approx(-__import__("math").log(0.7))


def test_accuracy_simple_case():
    assert accuracy_1x2("draw", "draw") == 1.0
    assert accuracy_1x2("team_a_win", "team_b_win") == 0.0


def test_actual_outcome_uses_match_goals():
    match = SimpleNamespace(team_a_goals=2, team_b_goals=1)
    assert actual_outcome(match) == "team_a_win"


def test_invalid_probabilities_fail_controlled_way():
    with pytest.raises(ValueError):
        validate_probability_triplet(0.8, 0.3, 0.1)


"""Pure evaluation metrics for 1X2 match predictions."""

from __future__ import annotations

import math
from typing import Any

PROBABILITY_TOLERANCE = 1e-6
VALID_OUTCOMES = ("team_a_win", "draw", "team_b_win")


def actual_outcome(match: Any) -> str:
    """Return the realized 1X2 outcome for a finished match."""
    team_a_goals = getattr(match, "team_a_goals", None)
    team_b_goals = getattr(match, "team_b_goals", None)
    if team_a_goals is None or team_b_goals is None:
        raise ValueError("match has no final goals available")
    if team_a_goals > team_b_goals:
        return "team_a_win"
    if team_a_goals < team_b_goals:
        return "team_b_win"
    return "draw"


def validate_probability_triplet(p_a: float, p_draw: float, p_b: float) -> None:
    """Validate a 1X2 probability triplet."""
    values = (float(p_a), float(p_draw), float(p_b))
    if any(value < 0 or value > 1 for value in values):
        raise ValueError("probabilities must be between 0 and 1")
    if abs(sum(values) - 1.0) > PROBABILITY_TOLERANCE:
        raise ValueError("probabilities must sum to 1")


def _actual_vector(outcome: str) -> tuple[float, float, float]:
    if outcome not in VALID_OUTCOMES:
        raise ValueError(f"invalid outcome: {outcome}")
    if outcome == "team_a_win":
        return (1.0, 0.0, 0.0)
    if outcome == "draw":
        return (0.0, 1.0, 0.0)
    return (0.0, 0.0, 1.0)


def brier_score_1x2(
    probabilities: dict[str, float],
    actual_outcome_value: str,
) -> float:
    """Return the multiclass Brier score for a 1X2 prediction."""
    p_a = float(probabilities["p_team_a_win_90"])
    p_draw = float(probabilities["p_draw_90"])
    p_b = float(probabilities["p_team_b_win_90"])
    validate_probability_triplet(p_a, p_draw, p_b)
    actual = _actual_vector(actual_outcome_value)
    predicted = (p_a, p_draw, p_b)
    return sum((pred - truth) ** 2 for pred, truth in zip(predicted, actual)) / 3.0


def log_loss_1x2(
    probabilities: dict[str, float],
    actual_outcome_value: str,
    epsilon: float = 1e-15,
) -> float:
    """Return the multiclass log loss for a 1X2 prediction."""
    p_a = float(probabilities["p_team_a_win_90"])
    p_draw = float(probabilities["p_draw_90"])
    p_b = float(probabilities["p_team_b_win_90"])
    validate_probability_triplet(p_a, p_draw, p_b)
    if actual_outcome_value not in VALID_OUTCOMES:
        raise ValueError(f"invalid outcome: {actual_outcome_value}")
    probability_by_outcome = {
        "team_a_win": p_a,
        "draw": p_draw,
        "team_b_win": p_b,
    }
    probability = min(max(probability_by_outcome[actual_outcome_value], epsilon), 1.0)
    return -math.log(probability)


def accuracy_1x2(predicted_outcome: str, actual_outcome_value: str) -> float:
    """Return 1.0 for a correct outcome prediction, else 0.0."""
    if predicted_outcome not in VALID_OUTCOMES:
        raise ValueError(f"invalid predicted outcome: {predicted_outcome}")
    if actual_outcome_value not in VALID_OUTCOMES:
        raise ValueError(f"invalid actual outcome: {actual_outcome_value}")
    return 1.0 if predicted_outcome == actual_outcome_value else 0.0

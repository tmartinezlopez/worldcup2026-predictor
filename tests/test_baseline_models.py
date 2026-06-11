import pytest

from src.models.baselines import (
    LogisticRegressionBaseline,
    MajorityClassBaseline,
    SimplePoissonBaseline,
)


def _row(target_result, **features):
    return {
        "target_result": target_result,
        "features_json": {
            "team_a_id": features.get("team_a_id", 1),
            "team_b_id": features.get("team_b_id", 2),
            "is_knockout": features.get("is_knockout", False),
            "neutral_site": features.get("neutral_site", True),
            "team_a_goals_for_recent": features.get("team_a_goals_for_recent", 6),
            "team_b_goals_for_recent": features.get("team_b_goals_for_recent", 4),
            "team_a_goals_against_recent": features.get(
                "team_a_goals_against_recent",
                3,
            ),
            "team_b_goals_against_recent": features.get(
                "team_b_goals_against_recent",
                5,
            ),
            "goals_for_recent_diff": features.get("goals_for_recent_diff", 2),
            "goals_against_recent_diff": features.get("goals_against_recent_diff", -2),
            "recent_form_points_diff": features.get("recent_form_points_diff", 3),
            "rating_points_diff": features.get("rating_points_diff", 15.0),
            "rank_diff": features.get("rank_diff", -2),
            "points_last_5_diff": features.get("points_last_5_diff", 4),
            "goal_diff_last_5_diff": features.get("goal_diff_last_5_diff", 3),
            "team_a_rating_points": features.get("team_a_rating_points", 1650.0),
            "team_b_rating_points": features.get("team_b_rating_points", 1635.0),
            "team_a_points_last_5": features.get("team_a_points_last_5", 10),
            "team_b_points_last_5": features.get("team_b_points_last_5", 6),
        },
    }


def _probability_sum(payload):
    return (
        payload["home_win_probability"]
        + payload["draw_probability"]
        + payload["away_win_probability"]
    )


def test_majority_baseline_works_with_tiny_data():
    model = MajorityClassBaseline().fit(
        [_row("team_a_win"), _row("team_a_win"), _row("draw")]
    )

    payload = model.predict_match(_row(None)["features_json"])

    assert payload["predicted_outcome"] == "team_a_win"
    assert payload["home_win_probability"] > payload["away_win_probability"]
    assert _probability_sum(payload) == pytest.approx(1.0)


def test_logistic_falls_back_if_insufficient_classes():
    model = LogisticRegressionBaseline(min_training_rows=2).fit(
        [_row("team_a_win"), _row("team_a_win")]
    )

    payload = model.predict_match(_row(None)["features_json"])

    assert model.fallback_used_ is True
    assert "class diversity" in model.fallback_reason_
    assert payload["home_win_probability"] == pytest.approx(1.0)
    assert _probability_sum(payload) == pytest.approx(1.0)


def test_probabilities_sum_approximately_one():
    rows = [
        _row("team_a_win", goals_for_recent_diff=4, recent_form_points_diff=5),
        _row("draw", goals_for_recent_diff=0, recent_form_points_diff=0),
        _row("team_b_win", goals_for_recent_diff=-4, recent_form_points_diff=-5),
        _row("team_a_win", goals_for_recent_diff=3, recent_form_points_diff=3),
        _row("team_b_win", goals_for_recent_diff=-3, recent_form_points_diff=-3),
    ]
    model = LogisticRegressionBaseline(min_training_rows=3).fit(rows)

    payload = model.predict_match(_row(None, goals_for_recent_diff=1)["features_json"])

    assert model.fallback_used_ is False
    assert _probability_sum(payload) == pytest.approx(1.0)


def test_poisson_outputs_valid_probabilities():
    model = SimplePoissonBaseline().fit(
        [
            _row("team_a_win", team_a_goals_for_recent=8, team_b_goals_for_recent=3),
            _row("draw", team_a_goals_for_recent=5, team_b_goals_for_recent=5),
        ],
        feature_config={"recent_form_window_matches": 5},
    )

    payload = model.predict_match(
        _row(
            None,
            team_a_goals_for_recent=10,
            team_b_goals_for_recent=5,
            team_a_goals_against_recent=4,
            team_b_goals_against_recent=6,
        )["features_json"]
    )

    assert payload["expected_goals_a"] > 0
    assert payload["expected_goals_b"] > 0
    assert 0 <= payload["home_win_probability"] <= 1
    assert 0 <= payload["draw_probability"] <= 1
    assert 0 <= payload["away_win_probability"] <= 1
    assert _probability_sum(payload) == pytest.approx(1.0, abs=1e-6)


def test_poisson_adjustment_keeps_lambdas_positive():
    model = SimplePoissonBaseline().fit(
        [
            _row("team_a_win", rating_points_diff=25.0, goal_diff_last_5_diff=4),
            _row("team_b_win", rating_points_diff=-20.0, goal_diff_last_5_diff=-3),
        ],
        feature_config={"recent_form_window_matches": 5},
    )

    payload = model.predict_match(
        _row(
            None,
            team_a_goals_for_recent=0,
            team_b_goals_for_recent=0,
            team_a_goals_against_recent=0,
            team_b_goals_against_recent=0,
            rating_points_diff=-9999.0,
            goal_diff_last_5_diff=-9999.0,
        )["features_json"]
    )

    assert model.poisson_adjustments_used_ is True
    assert payload["expected_goals_a"] > 0
    assert payload["expected_goals_b"] > 0

import pytest

from src.models.baselines import SimplePoissonBaseline


def _row(target_result, **features):
    return {
        "target_result": target_result,
        "features_json": {
            "team_a_goals_for_recent": features.get("team_a_goals_for_recent", 5),
            "team_b_goals_for_recent": features.get("team_b_goals_for_recent", 5),
            "team_a_goals_against_recent": features.get(
                "team_a_goals_against_recent", 5
            ),
            "team_b_goals_against_recent": features.get(
                "team_b_goals_against_recent", 5
            ),
            "rating_points_diff": features.get("rating_points_diff"),
            "goal_diff_last_5_diff": features.get("goal_diff_last_5_diff"),
        },
    }


def test_poisson_adjustment_strengthens_stronger_team():
    model = SimplePoissonBaseline().fit(
        [
            _row("team_a_win", rating_points_diff=40.0, goal_diff_last_5_diff=3),
            _row("team_b_win", rating_points_diff=-30.0, goal_diff_last_5_diff=-2),
        ],
        feature_config={"recent_form_window_matches": 5},
    )

    strong = model.predict_match(
        _row(None, rating_points_diff=80.0, goal_diff_last_5_diff=5)["features_json"]
    )
    weak = model.predict_match(
        _row(None, rating_points_diff=-80.0, goal_diff_last_5_diff=-5)["features_json"]
    )

    assert model.poisson_adjustments_used_ is True
    assert model.adjustment_features_used_ == [
        "rating_points_diff",
        "goal_diff_last_5_diff",
    ]
    assert strong["expected_goals_a"] > strong["expected_goals_b"]
    assert weak["expected_goals_a"] < weak["expected_goals_b"]
    assert strong["expected_goals_a"] > 0
    assert weak["expected_goals_b"] > 0


def test_poisson_adjustment_probabilities_stay_valid_under_extreme_inputs():
    model = SimplePoissonBaseline().fit(
        [_row("draw", rating_points_diff=0.0, goal_diff_last_5_diff=0.0)],
        feature_config={"recent_form_window_matches": 5},
    )

    payload = model.predict_match(
        _row(
            None,
            team_a_goals_for_recent=0,
            team_b_goals_for_recent=0,
            team_a_goals_against_recent=0,
            team_b_goals_against_recent=0,
            rating_points_diff=99999.0,
            goal_diff_last_5_diff=99999.0,
        )["features_json"]
    )

    assert payload["expected_goals_a"] > 0
    assert payload["expected_goals_b"] > 0
    assert payload["home_win_probability"] == pytest.approx(
        1.0 - payload["draw_probability"] - payload["away_win_probability"],
        abs=1e-6,
    )

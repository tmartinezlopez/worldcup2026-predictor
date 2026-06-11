from src.models.baselines import LogisticRegressionBaseline


def _row(target_result, **features):
    return {
        "target_result": target_result,
        "features_json": features,
    }


def test_logistic_uses_only_available_supported_features():
    rows = [
        _row(
            "team_a_win",
            rating_points_diff=20.0,
            points_last_5_diff=6,
            team_a_points_last_5=10,
        ),
        _row(
            "draw",
            rating_points_diff=0.0,
            points_last_5_diff=0,
            team_a_points_last_5=7,
        ),
        _row(
            "team_b_win",
            rating_points_diff=-15.0,
            points_last_5_diff=-5,
            team_a_points_last_5=3,
        ),
        _row(
            "team_a_win",
            rating_points_diff=12.0,
            points_last_5_diff=4,
            team_a_points_last_5=9,
        ),
        _row(
            "team_b_win",
            rating_points_diff=-11.0,
            points_last_5_diff=-4,
            team_a_points_last_5=4,
        ),
    ]

    model = LogisticRegressionBaseline(min_training_rows=3).fit(rows)

    assert model.fallback_used_ is False
    assert model.feature_names_ == [
        "rating_points_diff",
        "points_last_5_diff",
        "team_a_points_last_5",
    ]


def test_logistic_falls_back_when_supported_features_are_missing():
    rows = [
        _row("team_a_win", neutral_site=True),
        _row("draw", neutral_site=False),
        _row("team_b_win", neutral_site=True),
    ]

    model = LogisticRegressionBaseline(min_training_rows=3).fit(rows)

    assert model.fallback_used_ is True
    assert "no supported logistic features" in model.fallback_reason_

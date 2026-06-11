"""Baseline model implementations for the MVP model phase."""

from __future__ import annotations

import math
from collections import Counter
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression

RESULT_LABELS = ("team_a_win", "draw", "team_b_win")
LOGISTIC_CANDIDATE_FEATURE_NAMES = (
    "rating_points_diff",
    "rank_diff",
    "points_last_5_diff",
    "goal_diff_last_5_diff",
    "team_a_rating_points",
    "team_b_rating_points",
    "team_a_points_last_5",
    "team_b_points_last_5",
)


def _row_get(row: Any, key: str, default: Any = None) -> Any:
    if isinstance(row, dict):
        return row.get(key, default)
    return getattr(row, key, default)


def _row_features(row: Any) -> dict[str, Any]:
    return dict(_row_get(row, "features_json", {}) or {})


def _row_target(row: Any) -> str | None:
    value = _row_get(row, "target_result")
    return value if value in RESULT_LABELS else None


def normalize_probabilities(probabilities: dict[str, float]) -> dict[str, float]:
    clipped = {
        label: max(0.0, float(probabilities.get(label, 0.0))) for label in RESULT_LABELS
    }
    total = sum(clipped.values())
    if total <= 0:
        uniform = 1.0 / len(RESULT_LABELS)
        return {label: uniform for label in RESULT_LABELS}
    return {label: clipped[label] / total for label in RESULT_LABELS}


def probabilities_to_output(probabilities: dict[str, float]) -> dict[str, float]:
    normalized = normalize_probabilities(probabilities)
    return {
        "home_win_probability": normalized["team_a_win"],
        "draw_probability": normalized["draw"],
        "away_win_probability": normalized["team_b_win"],
    }


def predicted_outcome_from_probabilities(probabilities: dict[str, float]) -> str:
    normalized = normalize_probabilities(probabilities)
    return max(
        RESULT_LABELS,
        key=lambda label: (normalized[label], -RESULT_LABELS.index(label)),
    )


def default_scoreline_from_outcome(outcome: str) -> tuple[int, int]:
    if outcome == "team_a_win":
        return 1, 0
    if outcome == "team_b_win":
        return 0, 1
    return 1, 1


def build_prediction_payload(
    probabilities: dict[str, float],
    *,
    expected_goals_a: float | None = None,
    expected_goals_b: float | None = None,
    predicted_score_a: int | None = None,
    predicted_score_b: int | None = None,
) -> dict[str, Any]:
    normalized = normalize_probabilities(probabilities)
    outcome = predicted_outcome_from_probabilities(normalized)
    score_a = predicted_score_a
    score_b = predicted_score_b
    if score_a is None or score_b is None:
        score_a, score_b = default_scoreline_from_outcome(outcome)
    return {
        **probabilities_to_output(normalized),
        "predicted_outcome": outcome,
        "predicted_score_a": int(score_a),
        "predicted_score_b": int(score_b),
        "expected_goals_a": expected_goals_a,
        "expected_goals_b": expected_goals_b,
    }


class MajorityClassBaseline:
    """Return the historical 1X2 distribution from the training rows."""

    model_type = "majority"

    def __init__(self) -> None:
        self.class_probabilities_: dict[str, float] = normalize_probabilities(
            {label: 1.0 for label in RESULT_LABELS}
        )
        self.class_counts_: dict[str, int] = {label: 0 for label in RESULT_LABELS}
        self.training_rows_: int = 0
        self.warnings_: list[str] = []
        self.fallback_used_: bool = False
        self.fallback_reason_: str | None = None

    def fit(
        self,
        rows: list[Any],
        *,
        feature_config: dict[str, Any] | None = None,
    ) -> "MajorityClassBaseline":
        del feature_config
        counts = Counter(
            target
            for target in (_row_target(row) for row in rows)
            if target is not None
        )
        self.training_rows_ = len(rows)
        self.class_counts_ = {
            label: int(counts.get(label, 0)) for label in RESULT_LABELS
        }
        if sum(self.class_counts_.values()) == 0:
            self.warnings_ = [
                "no labeled training rows available; using uniform probabilities"
            ]
            probabilities = {label: 1.0 for label in RESULT_LABELS}
        else:
            self.warnings_ = []
            probabilities = self.class_counts_
        self.class_probabilities_ = normalize_probabilities(probabilities)
        return self

    def predict_proba(self, features_json: dict[str, Any]) -> dict[str, float]:
        del features_json
        return dict(self.class_probabilities_)

    def predict_match(self, features_json: dict[str, Any]) -> dict[str, Any]:
        return build_prediction_payload(self.predict_proba(features_json))


class LogisticRegressionBaseline:
    """Train a simple logistic regression on numeric feature store values."""

    model_type = "logistic"

    def __init__(self, *, min_training_rows: int = 5) -> None:
        self.min_training_rows = int(min_training_rows)
        self.feature_names_ = list(LOGISTIC_CANDIDATE_FEATURE_NAMES)
        self.model_: LogisticRegression | None = None
        self.fallback_model_ = MajorityClassBaseline()
        self.fallback_used_ = False
        self.fallback_reason_: str | None = None
        self.warnings_: list[str] = []
        self.training_rows_: int = 0
        self.observed_classes_: list[str] = []
        self.class_distribution_: dict[str, int] = {
            label: 0 for label in RESULT_LABELS
        }

    def _vectorize(self, features_json: dict[str, Any]) -> list[float]:
        values: list[float] = []
        for name in self.feature_names_:
            value = features_json.get(name, 0.0)
            if isinstance(value, bool):
                values.append(float(value))
            else:
                try:
                    values.append(float(value))
                except (TypeError, ValueError):
                    values.append(0.0)
        return values

    def fit(
        self,
        rows: list[Any],
        *,
        feature_config: dict[str, Any] | None = None,
    ) -> "LogisticRegressionBaseline":
        del feature_config
        labeled_rows = [row for row in rows if _row_target(row) is not None]
        self.training_rows_ = len(labeled_rows)
        self.observed_classes_ = sorted(
            {_row_target(row) for row in labeled_rows if _row_target(row)}
        )
        counts = Counter(
            target for target in (_row_target(row) for row in labeled_rows) if target
        )
        self.class_distribution_ = {
            label: int(counts.get(label, 0)) for label in RESULT_LABELS
        }
        self.feature_names_ = self._select_feature_names(labeled_rows)

        if self.training_rows_ < self.min_training_rows:
            self._use_fallback(
                rows,
                "insufficient training rows for logistic regression: "
                f"{self.training_rows_} < {self.min_training_rows}",
            )
            return self

        if len(self.observed_classes_) < 2:
            self._use_fallback(
                rows,
                "insufficient target class diversity for logistic regression",
            )
            return self

        if not self.feature_names_:
            self._use_fallback(
                rows,
                "no supported logistic features were available in the feature rows",
            )
            return self

        x_train = np.array(
            [self._vectorize(_row_features(row)) for row in labeled_rows]
        )
        y_train = np.array([_row_target(row) for row in labeled_rows])
        self.model_ = LogisticRegression(max_iter=1000, solver="lbfgs")
        self.model_.fit(x_train, y_train)
        self.fallback_used_ = False
        self.fallback_reason_ = None
        self.warnings_ = []
        return self

    def _select_feature_names(self, rows: list[Any]) -> list[str]:
        selected: list[str] = []
        for name in LOGISTIC_CANDIDATE_FEATURE_NAMES:
            if any(_row_features(row).get(name) is not None for row in rows):
                selected.append(name)
        return selected

    def _use_fallback(self, rows: list[Any], reason: str) -> None:
        self.fallback_model_.fit(rows)
        self.fallback_used_ = True
        self.fallback_reason_ = reason
        self.warnings_ = [reason]
        self.model_ = None

    def predict_proba(self, features_json: dict[str, Any]) -> dict[str, float]:
        if self.fallback_used_ or self.model_ is None:
            return self.fallback_model_.predict_proba(features_json)

        vector = np.array([self._vectorize(features_json)])
        proba = self.model_.predict_proba(vector)[0]
        probability_map = {label: 0.0 for label in RESULT_LABELS}
        for label, value in zip(self.model_.classes_, proba, strict=True):
            probability_map[str(label)] = float(value)
        return normalize_probabilities(probability_map)

    def predict_match(self, features_json: dict[str, Any]) -> dict[str, Any]:
        return build_prediction_payload(self.predict_proba(features_json))


class SimplePoissonBaseline:
    """Approximate 1X2 probabilities from recent goals features."""

    model_type = "poisson"

    def __init__(self) -> None:
        self.recent_form_window_matches_ = 5
        self.default_expected_goals_a_ = 1.2
        self.default_expected_goals_b_ = 1.0
        self.fallback_used_ = False
        self.fallback_reason_: str | None = None
        self.warnings_: list[str] = []
        self.poisson_adjustments_used_ = False
        self.adjustment_features_used_: list[str] = []
        self.last_expected_goals_: tuple[float, float] | None = None

    def fit(
        self,
        rows: list[Any],
        *,
        feature_config: dict[str, Any] | None = None,
    ) -> "SimplePoissonBaseline":
        config = feature_config or {}
        self.recent_form_window_matches_ = max(
            1, int(config.get("recent_form_window_matches", 5))
        )

        expected_goals_a_values: list[float] = []
        expected_goals_b_values: list[float] = []
        for row in rows:
            features = _row_features(row)
            home_xg, away_xg = self._estimate_expected_goals(features)
            expected_goals_a_values.append(home_xg)
            expected_goals_b_values.append(away_xg)

        if expected_goals_a_values:
            self.default_expected_goals_a_ = max(
                0.2, float(sum(expected_goals_a_values) / len(expected_goals_a_values))
            )
            self.default_expected_goals_b_ = max(
                0.2, float(sum(expected_goals_b_values) / len(expected_goals_b_values))
            )
        self.adjustment_features_used_ = self._detect_adjustment_features(rows)
        self.poisson_adjustments_used_ = bool(self.adjustment_features_used_)
        return self

    def _detect_adjustment_features(self, rows: list[Any]) -> list[str]:
        selected: list[str] = []
        for name in ("rating_points_diff", "goal_diff_last_5_diff"):
            if any(_row_features(row).get(name) is not None for row in rows):
                selected.append(name)
        return selected

    def _safe_recent_average(self, value: Any) -> float | None:
        try:
            recent_total = float(value)
        except (TypeError, ValueError):
            return None
        return max(0.0, recent_total) / float(self.recent_form_window_matches_)

    def _estimate_expected_goals(
        self, features_json: dict[str, Any]
    ) -> tuple[float, float]:
        home_attack = self._safe_recent_average(
            features_json.get("team_a_goals_for_recent")
        )
        away_attack = self._safe_recent_average(
            features_json.get("team_b_goals_for_recent")
        )
        home_defense = self._safe_recent_average(
            features_json.get("team_a_goals_against_recent")
        )
        away_defense = self._safe_recent_average(
            features_json.get("team_b_goals_against_recent")
        )

        expected_goals_a = None
        expected_goals_b = None
        if home_attack is not None and away_defense is not None:
            expected_goals_a = (home_attack + away_defense) / 2.0
        if away_attack is not None and home_defense is not None:
            expected_goals_b = (away_attack + home_defense) / 2.0

        if expected_goals_a is None:
            expected_goals_a = self.default_expected_goals_a_
            self.fallback_used_ = True
        if expected_goals_b is None:
            expected_goals_b = self.default_expected_goals_b_
            self.fallback_used_ = True

        expected_goals_a, expected_goals_b = self._apply_adjustments(
            features_json,
            expected_goals_a,
            expected_goals_b,
        )
        self.last_expected_goals_ = (expected_goals_a, expected_goals_b)
        return max(0.05, expected_goals_a), max(0.05, expected_goals_b)

    def _apply_adjustments(
        self,
        features_json: dict[str, Any],
        expected_goals_a: float,
        expected_goals_b: float,
    ) -> tuple[float, float]:
        adjustment = 0.0

        rating_points_diff = self._safe_float(features_json.get("rating_points_diff"))
        if rating_points_diff is not None:
            bounded_rating = max(-400.0, min(400.0, rating_points_diff))
            adjustment += bounded_rating / 2000.0

        goal_diff_last_5_diff = self._safe_float(
            features_json.get("goal_diff_last_5_diff")
        )
        if goal_diff_last_5_diff is not None:
            bounded_goal_diff = max(-10.0, min(10.0, goal_diff_last_5_diff))
            adjustment += bounded_goal_diff / 50.0

        adjustment = max(-0.25, min(0.25, adjustment))
        return (
            max(0.05, expected_goals_a + adjustment),
            max(0.05, expected_goals_b - adjustment),
        )

    def _safe_float(self, value: Any) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _poisson_pmf(self, goals: int, lambda_value: float) -> float:
        return math.exp(-lambda_value) * (lambda_value**goals) / math.factorial(goals)

    def _probability_grid(
        self, expected_goals_a: float, expected_goals_b: float, max_goals: int = 10
    ) -> tuple[dict[str, float], tuple[int, int]]:
        home_win = 0.0
        draw = 0.0
        away_win = 0.0
        best_score = (0, 0)
        best_score_probability = -1.0
        for home_goals in range(max_goals + 1):
            home_p = self._poisson_pmf(home_goals, expected_goals_a)
            for away_goals in range(max_goals + 1):
                score_probability = home_p * self._poisson_pmf(
                    away_goals,
                    expected_goals_b,
                )
                if score_probability > best_score_probability:
                    best_score = (home_goals, away_goals)
                    best_score_probability = score_probability
                if home_goals > away_goals:
                    home_win += score_probability
                elif home_goals < away_goals:
                    away_win += score_probability
                else:
                    draw += score_probability

        probabilities = normalize_probabilities(
            {
                "team_a_win": home_win,
                "draw": draw,
                "team_b_win": away_win,
            }
        )
        return probabilities, best_score

    def predict_proba(self, features_json: dict[str, Any]) -> dict[str, float]:
        expected_goals_a, expected_goals_b = self._estimate_expected_goals(
            features_json
        )
        probabilities, _ = self._probability_grid(expected_goals_a, expected_goals_b)
        return probabilities

    def predict_match(self, features_json: dict[str, Any]) -> dict[str, Any]:
        expected_goals_a, expected_goals_b = self._estimate_expected_goals(
            features_json
        )
        probabilities, best_score = self._probability_grid(
            expected_goals_a,
            expected_goals_b,
        )
        return build_prediction_payload(
            probabilities,
            expected_goals_a=expected_goals_a,
            expected_goals_b=expected_goals_b,
            predicted_score_a=best_score[0],
            predicted_score_b=best_score[1],
        )

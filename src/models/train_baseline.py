"""Train baseline models from a stored feature set."""

from __future__ import annotations

import argparse
import json
import math
import pickle
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.connection import get_session
from src.db.models import FeatureSet, Match, MatchFeature, ModelRun
from src.models.baselines import (
    RESULT_LABELS,
    LogisticRegressionBaseline,
    MajorityClassBaseline,
    SimplePoissonBaseline,
)

REPORTS_ROOT = Path("data/processed/model_reports")
SUPPORTED_MODEL_TYPES = ("majority", "logistic", "poisson")


def _label_probability_keys() -> dict[str, str]:
    return {
        "team_a_win": "home_win_probability",
        "draw": "draw_probability",
        "team_b_win": "away_win_probability",
    }


def _build_model(model_type: str) -> Any:
    if model_type == "majority":
        return MajorityClassBaseline()
    if model_type == "logistic":
        return LogisticRegressionBaseline()
    if model_type == "poisson":
        return SimplePoissonBaseline()
    raise ValueError(f"unsupported model type: {model_type}")


def _multiclass_log_loss(rows: list[MatchFeature], model: Any) -> float | None:
    if not rows:
        return None
    loss = 0.0
    key_map = _label_probability_keys()
    for row in rows:
        prediction = model.predict_match(row.features_json)
        target = row.target_result
        if target not in key_map:
            continue
        probability = max(1e-12, float(prediction[key_map[target]]))
        loss += -math.log(probability)
    return loss / len(rows)


def _training_accuracy(rows: list[MatchFeature], model: Any) -> float | None:
    if not rows:
        return None
    correct = 0
    for row in rows:
        predicted = model.predict_match(row.features_json)["predicted_outcome"]
        if predicted == row.target_result:
            correct += 1
    return correct / len(rows)


def _write_model_report(report_dir: Path, report: dict[str, Any]) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "model_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )

    lines = [
        "# Model Report",
        "",
        f"- Model run id: {report['model_run_id']}",
        f"- Model type: `{report['model_type']}`",
        f"- Model family: `{report['model_family']}`",
        f"- Feature set id: {report['feature_set_id']}",
        f"- Training rows: {report['training_rows']}",
        f"- Prediction rows available: {report['prediction_rows_available']}",
        f"- Fallback used: `{report['fallback_used']}`",
        f"- Fallback reason: `{report.get('fallback_reason')}`",
        "",
        "## Features Used",
    ]
    features_used = report.get("features_used") or []
    if features_used:
        lines.extend(f"- `{feature_name}`" for feature_name in features_used)
    else:
        lines.append("- None.")
    lines.extend(
        [
            "",
            "## Class Distribution",
        ]
    )
    class_distribution = report.get("class_distribution") or {}
    if class_distribution:
        for label, value in sorted(class_distribution.items()):
            lines.append(f"- `{label}`: {value}")
    else:
        lines.append("- None.")
    lines.extend(
        [
            "",
            "## Data Quality Warnings",
        ]
    )
    data_quality_warnings = report.get("data_quality_warnings") or []
    if data_quality_warnings:
        lines.extend(f"- {warning}" for warning in data_quality_warnings)
    else:
        lines.append("- None.")
    lines.extend(
        [
            "",
        "## Metrics",
        ]
    )
    for key, value in sorted(report["metrics"].items()):
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Warnings"])
    if report["warnings"]:
        lines.extend(f"- {warning}" for warning in report["warnings"])
    else:
        lines.append("- None.")
    (report_dir / "model_report.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def train_baseline_model(
    session: Session,
    *,
    feature_set_id: int,
    model_type: str,
    report_root: Path | None = None,
) -> dict[str, Any]:
    if model_type not in SUPPORTED_MODEL_TYPES:
        raise ValueError(f"unsupported model type: {model_type}")

    feature_set = session.scalar(
        select(FeatureSet).where(FeatureSet.id == feature_set_id)
    )
    if feature_set is None:
        raise ValueError(f"unknown feature set id: {feature_set_id}")

    all_rows = session.scalars(
        select(MatchFeature)
        .where(MatchFeature.feature_set_id == feature_set_id)
        .order_by(MatchFeature.id)
    ).all()
    training_rows = [row for row in all_rows if row.target_result is not None]
    prediction_rows = [row for row in all_rows if row.target_result is None]
    model = _build_model(model_type)
    model.fit(training_rows, feature_config=feature_set.feature_config_json or {})

    match_dates = session.execute(
        select(Match.date).join(MatchFeature, MatchFeature.match_id == Match.id).where(
            MatchFeature.feature_set_id == feature_set_id,
            MatchFeature.target_result.is_not(None),
        )
    ).scalars().all()
    training_dates = [item for item in match_dates if item is not None]

    class_distribution = Counter(
        row.target_result for row in training_rows if row.target_result
    )
    features_used = list(getattr(model, "feature_names_", []))
    fallback_reason = getattr(model, "fallback_reason_", None)
    data_quality_warnings = list(
        (feature_set.data_coverage_json or {}).get("data_quality_warnings", [])
    )
    metrics = {
        "training_rows": len(training_rows),
        "prediction_rows_available": len(prediction_rows),
        "class_distribution": {
            label: int(class_distribution.get(label, 0)) for label in RESULT_LABELS
        },
        "train_accuracy": _training_accuracy(training_rows, model),
        "train_log_loss": _multiclass_log_loss(training_rows, model),
        "fallback_used": bool(getattr(model, "fallback_used_", False)),
        "fallback_reason": fallback_reason,
        "features_used": features_used,
        "model_family": model_type,
        "data_quality_warnings": data_quality_warnings,
        "poisson_adjustments_used": bool(
            getattr(model, "poisson_adjustments_used_", False)
        ),
        "adjustment_features_used": list(
            getattr(model, "adjustment_features_used_", [])
        ),
    }
    warnings = list(getattr(model, "warnings_", []))

    model_run = ModelRun(
        model_name=f"baseline_{model_type}",
        model_version="phase13_mvp_v1",
        trained_at=datetime.now(UTC),
        training_start_date=min(training_dates) if training_dates else None,
        training_end_date=max(training_dates) if training_dates else None,
        feature_set_id=feature_set.id,
        features_used_json={
            "model_type": model_type,
            "model_family": model_type,
            "features_used": features_used,
            "feature_set_version": feature_set.version,
            "feature_config": feature_set.feature_config_json or {},
        },
        metrics_json={
            **metrics,
            "warnings": warnings,
        },
        artifact_path=None,
        notes="; ".join(warnings) if warnings else None,
    )
    session.add(model_run)
    session.flush()

    report_root = report_root or REPORTS_ROOT
    report_dir = report_root / str(model_run.id)
    report_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = report_dir / "model_artifact.pkl"
    with artifact_path.open("wb") as artifact_file:
        pickle.dump(model, artifact_file)
    model_run.artifact_path = str(artifact_path)

    report = {
        "model_run_id": model_run.id,
        "model_type": model_type,
        "model_family": model_type,
        "feature_set_id": feature_set.id,
        "training_rows": len(training_rows),
        "prediction_rows_available": len(prediction_rows),
        "metrics": metrics,
        "features_used": features_used,
        "fallback_reason": fallback_reason,
        "class_distribution": metrics["class_distribution"],
        "data_quality_warnings": data_quality_warnings,
        "poisson_adjustments_used": metrics["poisson_adjustments_used"],
        "adjustment_features_used": metrics["adjustment_features_used"],
        "warnings": warnings,
        "fallback_used": bool(getattr(model, "fallback_used_", False)),
        "artifact_path": str(artifact_path),
    }
    _write_model_report(report_dir, report)
    session.commit()
    report["report_dir"] = str(report_dir)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a baseline model")
    parser.add_argument("--feature-set-id", required=True, type=int)
    parser.add_argument("--model-type", required=True, choices=SUPPORTED_MODEL_TYPES)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with get_session() as session:
        report = train_baseline_model(
            session,
            feature_set_id=args.feature_set_id,
            model_type=args.model_type,
        )
    print(f"model_run_id={report['model_run_id']}")
    print(f"report_dir={report['report_dir']}")


if __name__ == "__main__":
    main()

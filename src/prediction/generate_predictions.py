"""Generate draft predictions from a stored model run."""

from __future__ import annotations

import argparse
import json
import pickle
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.connection import get_session
from src.db.models import FeatureSet, Match, MatchFeature, ModelRun, Prediction

REPORTS_ROOT = Path("data/processed/model_reports")


def _confidence_label(probability: float) -> str:
    if probability >= 0.6:
        return "high"
    if probability >= 0.45:
        return "medium"
    return "low"


def _read_existing_report(report_dir: Path) -> dict[str, Any]:
    report_path = report_dir / "model_report.json"
    if not report_path.is_file():
        return {}
    return json.loads(report_path.read_text(encoding="utf-8"))


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
        f"- Model family: `{report.get('model_family', report['model_type'])}`",
        f"- Feature set id: {report['feature_set_id']}",
        f"- Training rows: {report['training_rows']}",
        f"- Prediction rows available: {report['prediction_rows_available']}",
        f"- Predictions created: {report.get('predictions_created', 0)}",
        f"- Predictions skipped: {report.get('predictions_skipped', 0)}",
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
    lines.extend(["", "## Metrics"])
    for key, value in sorted((report.get("metrics") or {}).items()):
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Class Distribution"])
    class_distribution = report.get("class_distribution") or {}
    if class_distribution:
        for key, value in sorted(class_distribution.items()):
            lines.append(f"- `{key}`: {value}")
    else:
        lines.append("- None.")
    lines.extend(["", "## Data Quality Warnings"])
    data_quality_warnings = report.get("data_quality_warnings") or []
    if data_quality_warnings:
        lines.extend(f"- {warning}" for warning in data_quality_warnings)
    else:
        lines.append("- None.")
    lines.extend(["", "## Warnings"])
    warnings = report.get("warnings") or []
    if warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- None.")
    (report_dir / "model_report.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def generate_predictions(
    session: Session,
    *,
    model_run_id: int,
    report_root: Path | None = None,
) -> dict[str, Any]:
    model_run = session.scalar(select(ModelRun).where(ModelRun.id == model_run_id))
    if model_run is None:
        raise ValueError(f"unknown model run id: {model_run_id}")
    if not model_run.artifact_path:
        raise ValueError("model run has no artifact_path")
    if model_run.feature_set_id is None:
        raise ValueError("model run is not linked to a feature set")

    feature_set = session.scalar(
        select(FeatureSet).where(FeatureSet.id == model_run.feature_set_id)
    )
    if feature_set is None:
        raise ValueError(
            "feature set not found for model run: "
            f"{model_run.feature_set_id}"
        )

    with Path(model_run.artifact_path).open("rb") as artifact_file:
        model = pickle.load(artifact_file)  # noqa: S301

    prediction_rows = session.scalars(
        select(MatchFeature)
        .join(Match, Match.id == MatchFeature.match_id)
        .where(
            MatchFeature.feature_set_id == feature_set.id,
            MatchFeature.target_result.is_(None),
            Match.status == "scheduled",
        )
        .order_by(MatchFeature.id)
    ).all()

    warnings: list[str] = []
    predictions_created = 0
    predictions_skipped = 0
    for row in prediction_rows:
        batch_id = feature_set.batch_id
        if batch_id is None:
            warnings.append(
                f"match_feature_id={row.id} skipped because feature set has no batch_id"
            )
            predictions_skipped += 1
            continue

        existing = session.scalar(
            select(Prediction).where(
                Prediction.match_id == row.match_id,
                Prediction.model_run_id == model_run.id,
            )
        )
        if existing is not None:
            predictions_skipped += 1
            continue

        payload = model.predict_match(row.features_json)
        probability_values = [
            payload["home_win_probability"],
            payload["draw_probability"],
            payload["away_win_probability"],
        ]
        max_probability = float(max(probability_values))

        session.add(
            Prediction(
                match_id=row.match_id,
                batch_id=batch_id,
                model_run_id=model_run.id,
                feature_set_id=feature_set.id,
                predicted_at=datetime.now(UTC),
                prediction_deadline=feature_set.cutoff_time,
                is_official=False,
                is_frozen=False,
                predicted_score_a=int(payload["predicted_score_a"]),
                predicted_score_b=int(payload["predicted_score_b"]),
                predicted_outcome=str(payload["predicted_outcome"]),
                p_team_a_win_90=float(payload["home_win_probability"]),
                p_draw_90=float(payload["draw_probability"]),
                p_team_b_win_90=float(payload["away_win_probability"]),
                expected_goals_a=payload.get("expected_goals_a"),
                expected_goals_b=payload.get("expected_goals_b"),
                confidence_score=max_probability,
                confidence_label=_confidence_label(max_probability),
                explanation_json={
                    "model_name": model_run.model_name,
                    "model_version": model_run.model_version,
                    "draft_prediction": True,
                },
                data_coverage_json={
                    "feature_set_id": feature_set.id,
                    "feature_row_id": row.id,
                },
            )
        )
        predictions_created += 1

    report_root = report_root or REPORTS_ROOT
    report_dir = report_root / str(model_run.id)
    report = _read_existing_report(report_dir)
    report.update(
        {
            "model_run_id": model_run.id,
            "model_type": (model_run.features_used_json or {}).get(
                "model_type",
                model_run.model_name,
            ),
            "model_family": (model_run.features_used_json or {}).get(
                "model_family",
                (model_run.features_used_json or {}).get(
                    "model_type",
                    model_run.model_name,
                ),
            ),
            "feature_set_id": feature_set.id,
            "training_rows": (model_run.metrics_json or {}).get("training_rows", 0),
            "prediction_rows_available": len(prediction_rows),
            "metrics": model_run.metrics_json or {},
            "features_used": (model_run.features_used_json or {}).get(
                "features_used",
                [],
            ),
            "fallback_reason": (model_run.metrics_json or {}).get(
                "fallback_reason"
            ),
            "class_distribution": (model_run.metrics_json or {}).get(
                "class_distribution",
                {},
            ),
            "data_quality_warnings": (model_run.metrics_json or {}).get(
                "data_quality_warnings",
                [],
            ),
            "warnings": sorted(set([*(report.get("warnings") or []), *warnings])),
            "fallback_used": bool(
                (model_run.metrics_json or {}).get("fallback_used", False)
            ),
            "predictions_created": predictions_created,
            "predictions_skipped": predictions_skipped,
            "predictions_generated_at": datetime.now(UTC).isoformat(),
        }
    )
    _write_model_report(report_dir, report)
    session.commit()
    report["report_dir"] = str(report_dir)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate draft predictions")
    parser.add_argument("--model-run-id", required=True, type=int)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with get_session() as session:
        report = generate_predictions(session, model_run_id=args.model_run_id)
    print(f"predictions_created={report['predictions_created']}")
    print(f"report_dir={report['report_dir']}")


if __name__ == "__main__":
    main()

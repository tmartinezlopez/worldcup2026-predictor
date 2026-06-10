"""Evaluate stored predictions against finished matches."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.connection import get_session
from src.db.models import EvaluationResult, Match, ModelRun, Prediction
from src.evaluation.metrics import (
    accuracy_1x2,
    actual_outcome,
    brier_score_1x2,
    log_loss_1x2,
)

REPORTS_ROOT = Path("data/processed/evaluation_reports")


def _write_evaluation_report(report_dir: Path, report: dict[str, Any]) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "evaluation_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    lines = [
        "# Evaluation Report",
        "",
        f"- Model run id: {report['model_run_id']}",
        f"- Evaluated predictions: {report['evaluated_predictions']}",
        f"- Skipped predictions: {report['skipped_predictions']}",
        f"- Accuracy: {report['accuracy']}",
        f"- Mean Brier score: {report['mean_brier_score']}",
        f"- Mean log loss: {report['mean_log_loss']}",
        "",
        "## Warnings",
    ]
    if report["warnings"]:
        lines.extend(f"- {warning}" for warning in report["warnings"])
    else:
        lines.append("- None.")
    (report_dir / "evaluation_report.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def evaluate_predictions(
    session: Session,
    *,
    model_run_id: int,
    report_root: Path | None = None,
) -> dict[str, Any]:
    model_run = session.scalar(select(ModelRun).where(ModelRun.id == model_run_id))
    if model_run is None:
        raise ValueError(f"unknown model run id: {model_run_id}")

    predictions = session.scalars(
        select(Prediction)
        .where(Prediction.model_run_id == model_run_id)
        .order_by(Prediction.id)
    ).all()

    warnings: list[str] = []
    evaluated_ids: list[int] = []
    evaluated_predictions = 0
    skipped_predictions = 0
    total_accuracy = 0.0
    total_brier = 0.0
    total_log_loss = 0.0

    for prediction in predictions:
        match = session.scalar(select(Match).where(Match.id == prediction.match_id))
        if match is None:
            warnings.append(
                f"prediction_id={prediction.id} skipped because match is missing"
            )
            skipped_predictions += 1
            continue
        if (
            match.status != "finished"
            or match.team_a_goals is None
            or match.team_b_goals is None
        ):
            warnings.append(
                f"prediction_id={prediction.id} skipped because match status is "
                f"`{match.status}` or goals are unavailable"
            )
            skipped_predictions += 1
            continue

        outcome = actual_outcome(match)
        probability_map = {
            "p_team_a_win_90": prediction.p_team_a_win_90,
            "p_draw_90": prediction.p_draw_90,
            "p_team_b_win_90": prediction.p_team_b_win_90,
        }
        accuracy = accuracy_1x2(prediction.predicted_outcome, outcome)
        brier = brier_score_1x2(probability_map, outcome)
        log_loss = log_loss_1x2(probability_map, outcome)

        existing = session.scalar(
            select(EvaluationResult).where(
                EvaluationResult.prediction_id == prediction.id
            )
        )
        if existing is None:
            evaluation_result = EvaluationResult(
                prediction_id=prediction.id,
                match_id=match.id,
                batch_id=prediction.batch_id,
                evaluated_at=datetime.now(UTC),
                actual_score_a=match.team_a_goals,
                actual_score_b=match.team_b_goals,
                actual_outcome=outcome,
                log_loss=log_loss,
                brier_score=brier,
                is_correct_outcome=bool(accuracy),
                is_correct_score=(
                    prediction.predicted_score_a == match.team_a_goals
                    and prediction.predicted_score_b == match.team_b_goals
                ),
                notes=f"model_run_id={model_run_id}",
            )
            session.add(evaluation_result)
            session.flush()
            evaluated_ids.append(evaluation_result.id)
        else:
            existing.evaluated_at = datetime.now(UTC)
            existing.actual_score_a = match.team_a_goals
            existing.actual_score_b = match.team_b_goals
            existing.actual_outcome = outcome
            existing.log_loss = log_loss
            existing.brier_score = brier
            existing.is_correct_outcome = bool(accuracy)
            existing.is_correct_score = (
                prediction.predicted_score_a == match.team_a_goals
                and prediction.predicted_score_b == match.team_b_goals
            )
            existing.notes = f"model_run_id={model_run_id}"
            evaluated_ids.append(existing.id)

        evaluated_predictions += 1
        skipped_predictions = max(0, len(predictions) - evaluated_predictions)
        total_accuracy += accuracy
        total_brier += brier
        total_log_loss += log_loss

    if evaluated_predictions == 0:
        warnings.append("no finished predictions were available for evaluation")
        accuracy_value = None
        mean_brier = None
        mean_log_loss = None
        report_dir_name = f"model_run_{model_run_id}_empty"
    else:
        accuracy_value = total_accuracy / evaluated_predictions
        mean_brier = total_brier / evaluated_predictions
        mean_log_loss = total_log_loss / evaluated_predictions
        report_dir_name = str(evaluated_ids[0])

    report = {
        "model_run_id": model_run_id,
        "evaluated_predictions": evaluated_predictions,
        "skipped_predictions": len(predictions) - evaluated_predictions,
        "accuracy": accuracy_value,
        "mean_brier_score": mean_brier,
        "mean_log_loss": mean_log_loss,
        "warnings": warnings,
        "evaluation_result_ids": evaluated_ids,
    }
    report_root = report_root or REPORTS_ROOT
    report_dir = report_root / report_dir_name
    _write_evaluation_report(report_dir, report)
    session.commit()
    report["report_dir"] = str(report_dir)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate predictions for one model run"
    )
    parser.add_argument("--model-run-id", required=True, type=int)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with get_session() as session:
        report = evaluate_predictions(session, model_run_id=args.model_run_id)
    print(f"evaluated_predictions={report['evaluated_predictions']}")
    print(f"report_dir={report['report_dir']}")


if __name__ == "__main__":
    main()

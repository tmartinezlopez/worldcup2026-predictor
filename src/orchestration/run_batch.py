"""Run one batch end-to-end with the MVP orchestration flow."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from src.db.connection import get_session
from src.evaluation.evaluate_predictions import evaluate_predictions
from src.features.build_feature_store import build_feature_store
from src.models.train_baseline import SUPPORTED_MODEL_TYPES, train_baseline_model
from src.prediction.freeze_predictions import freeze_predictions
from src.prediction.generate_predictions import generate_predictions

REPORTS_ROOT = Path("data/processed/batch_runs")


def _write_batch_run_report(report_dir: Path, report: dict[str, Any]) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "batch_run_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    lines = [
        "# Batch Run Report",
        "",
        f"- Batch code: `{report['batch_code']}`",
        f"- Model type: `{report['model_type']}`",
        f"- Feature set id: {report.get('feature_set_id')}",
        f"- Model run id: {report.get('model_run_id')}",
        f"- Predictions created: {report.get('predictions_created')}",
        f"- Evaluation skipped: `{report['skip_evaluation']}`",
        f"- Freeze requested: `{report['freeze_requested']}`",
        "",
        "## Steps",
    ]
    for step_name, step in report["steps"].items():
        lines.append(f"- `{step_name}`: `{step['status']}`")
    lines.extend(["", "## Warnings"])
    if report["warnings"]:
        lines.extend(f"- {warning}" for warning in report["warnings"])
    else:
        lines.append("- None.")
    (report_dir / "batch_run_report.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def run_batch(
    session: Session,
    *,
    batch_code: str,
    model_type: str,
    freeze: bool,
    allow_after_cutoff: bool,
    skip_evaluation: bool,
    yes_run: bool,
    report_root: Path | None = None,
) -> dict[str, Any]:
    if not yes_run:
        raise ValueError("--yes-run is required to execute batch orchestration")
    if model_type not in SUPPORTED_MODEL_TYPES:
        raise ValueError(f"unsupported model type: {model_type}")

    warnings: list[str] = []
    steps: dict[str, dict[str, Any]] = {}

    feature_report = build_feature_store(session=session, batch_code=batch_code)
    steps["build_feature_store"] = {
        "status": "completed",
        "feature_set_id": feature_report["feature_set_id"],
        "report_dir": feature_report["report_dir"],
    }

    train_report = train_baseline_model(
        session,
        feature_set_id=feature_report["feature_set_id"],
        model_type=model_type,
    )
    steps["train_baseline"] = {
        "status": "completed",
        "model_run_id": train_report["model_run_id"],
        "report_dir": train_report["report_dir"],
        "fallback_used": train_report["fallback_used"],
    }
    warnings.extend(train_report.get("warnings", []))

    prediction_report = generate_predictions(
        session,
        model_run_id=train_report["model_run_id"],
    )
    steps["generate_predictions"] = {
        "status": "completed",
        "predictions_created": prediction_report["predictions_created"],
        "predictions_skipped": prediction_report["predictions_skipped"],
        "report_dir": prediction_report["report_dir"],
    }
    warnings.extend(prediction_report.get("warnings", []))

    evaluation_report: dict[str, Any] | None = None
    if skip_evaluation:
        steps["evaluate_predictions"] = {
            "status": "skipped",
            "reason": "--skip-evaluation was provided",
        }
    else:
        evaluation_report = evaluate_predictions(
            session,
            model_run_id=train_report["model_run_id"],
        )
        steps["evaluate_predictions"] = {
            "status": "completed",
            "evaluated_predictions": evaluation_report["evaluated_predictions"],
            "skipped_predictions": evaluation_report["skipped_predictions"],
            "report_dir": evaluation_report["report_dir"],
        }
        warnings.extend(evaluation_report.get("warnings", []))

    freeze_report: dict[str, Any] | None = None
    if freeze:
        freeze_report = freeze_predictions(
            session,
            model_run_id=train_report["model_run_id"],
            batch_code=batch_code,
            yes_freeze=True,
            allow_after_cutoff=allow_after_cutoff,
        )
        steps["freeze_predictions"] = {
            "status": (
                "completed"
                if freeze_report["frozen_count"] > 0
                else "completed_with_skips"
            ),
            "frozen_count": freeze_report["frozen_count"],
            "skipped_count": freeze_report["skipped_count"],
            "report_dir": freeze_report["report_dir"],
        }
        warnings.extend(freeze_report.get("reasons", []))
        if (
            freeze_report["frozen_count"] == 0
            and any("cutoff_time" in reason for reason in freeze_report["reasons"])
            and not allow_after_cutoff
        ):
            warnings.append(
                "freeze skipped after cutoff; rerun with "
                "--allow-after-cutoff for development/testing"
            )
    else:
        steps["freeze_predictions"] = {
            "status": "skipped",
            "reason": "--freeze was not provided",
        }

    run_timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    report = {
        "batch_code": batch_code,
        "model_type": model_type,
        "feature_set_id": feature_report["feature_set_id"],
        "model_run_id": train_report["model_run_id"],
        "predictions_created": prediction_report["predictions_created"],
        "skip_evaluation": skip_evaluation,
        "freeze_requested": freeze,
        "allow_after_cutoff": allow_after_cutoff,
        "steps": steps,
        "warnings": sorted(set(warnings)),
    }
    if evaluation_report is not None:
        report["evaluation_result_ids"] = evaluation_report["evaluation_result_ids"]
    if freeze_report is not None:
        report["frozen_count"] = freeze_report["frozen_count"]

    report_root = report_root or REPORTS_ROOT
    report_dir = report_root / f"{batch_code}_{run_timestamp}"
    _write_batch_run_report(report_dir, report)
    report["report_dir"] = str(report_dir)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one batch end-to-end")
    parser.add_argument("--batch-code", required=True)
    parser.add_argument("--model-type", required=True, choices=SUPPORTED_MODEL_TYPES)
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--allow-after-cutoff", action="store_true")
    parser.add_argument("--skip-evaluation", action="store_true")
    parser.add_argument("--yes-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with get_session() as session:
        report = run_batch(
            session,
            batch_code=args.batch_code,
            model_type=args.model_type,
            freeze=args.freeze,
            allow_after_cutoff=args.allow_after_cutoff,
            skip_evaluation=args.skip_evaluation,
            yes_run=args.yes_run,
        )
    print(f"feature_set_id={report['feature_set_id']}")
    print(f"model_run_id={report['model_run_id']}")
    print(f"predictions_created={report['predictions_created']}")
    print(f"report_dir={report['report_dir']}")


if __name__ == "__main__":
    main()

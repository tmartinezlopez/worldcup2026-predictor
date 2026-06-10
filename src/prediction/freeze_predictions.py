"""Freeze draft predictions as official predictions for one batch."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.connection import get_session
from src.db.models import Batch, ModelRun, Prediction

REPORTS_ROOT = Path("data/processed/freeze_reports")


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _write_freeze_report(report_dir: Path, report: dict[str, Any]) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "freeze_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    lines = [
        "# Freeze Report",
        "",
        f"- Model run id: {report['model_run_id']}",
        f"- Batch code: `{report['batch_code']}`",
        f"- Frozen count: {report['frozen_count']}",
        f"- Skipped count: {report['skipped_count']}",
        f"- Freeze executed: `{report['freeze_executed']}`",
        "",
        "## Reasons",
    ]
    if report["reasons"]:
        lines.extend(f"- {reason}" for reason in report["reasons"])
    else:
        lines.append("- None.")
    (report_dir / "freeze_report.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def freeze_predictions(
    session: Session,
    *,
    model_run_id: int,
    batch_code: str,
    yes_freeze: bool,
    allow_after_cutoff: bool = False,
    report_root: Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    model_run = session.scalar(select(ModelRun).where(ModelRun.id == model_run_id))
    if model_run is None:
        raise ValueError(f"unknown model run id: {model_run_id}")

    batch = session.scalar(select(Batch).where(Batch.code == batch_code))
    if batch is None:
        raise ValueError(f"unknown batch code: {batch_code}")
    if batch.cutoff_time is None:
        raise ValueError("batch has no cutoff_time configured")

    current_time = _ensure_utc(now or datetime.now(UTC))
    cutoff_time = _ensure_utc(batch.cutoff_time)
    reasons: list[str] = []

    predictions = session.scalars(
        select(Prediction)
        .where(
            Prediction.model_run_id == model_run_id,
            Prediction.batch_id == batch.id,
        )
        .order_by(Prediction.id)
    ).all()

    if not yes_freeze:
        reasons.append("--yes-freeze is required to write official predictions")
    if current_time > cutoff_time and not allow_after_cutoff:
        reasons.append("current time is after batch cutoff_time")

    frozen_count = 0
    skipped_count = 0
    if reasons:
        skipped_count = len(predictions)
    else:
        for prediction in predictions:
            if prediction.is_official or prediction.is_frozen:
                skipped_count += 1
                reasons.append(
                    "prediction_id="
                    f"{prediction.id} skipped because it is already official/frozen"
                )
                continue

            conflicting = session.scalar(
                select(Prediction).where(
                    Prediction.match_id == prediction.match_id,
                    Prediction.batch_id == batch.id,
                    Prediction.model_run_id != model_run_id,
                    (Prediction.is_official.is_(True) | Prediction.is_frozen.is_(True)),
                )
            )
            if conflicting is not None:
                skipped_count += 1
                reasons.append(
                    "prediction_id="
                    f"{prediction.id} skipped because match_id={prediction.match_id} "
                    "already has an official/frozen prediction"
                )
                continue

            prediction.is_official = True
            prediction.is_frozen = True
            frozen_count += 1

    report = {
        "model_run_id": model_run_id,
        "batch_code": batch_code,
        "batch_id": batch.id,
        "cutoff_time": cutoff_time.isoformat(),
        "frozen_count": frozen_count,
        "skipped_count": skipped_count,
        "freeze_executed": yes_freeze and not (
            current_time > cutoff_time and not allow_after_cutoff
        ),
        "allow_after_cutoff": allow_after_cutoff,
        "reasons": reasons,
    }
    report_root = report_root or REPORTS_ROOT
    report_dir = report_root / f"{batch_code}_{current_time.strftime('%Y%m%dT%H%M%SZ')}"
    _write_freeze_report(report_dir, report)
    session.commit()
    report["report_dir"] = str(report_dir)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Freeze draft predictions as official predictions"
    )
    parser.add_argument("--model-run-id", required=True, type=int)
    parser.add_argument("--batch-code", required=True)
    parser.add_argument("--yes-freeze", action="store_true")
    parser.add_argument("--allow-after-cutoff", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with get_session() as session:
        report = freeze_predictions(
            session,
            model_run_id=args.model_run_id,
            batch_code=args.batch_code,
            yes_freeze=args.yes_freeze,
            allow_after_cutoff=args.allow_after_cutoff,
        )
    print(f"frozen_count={report['frozen_count']}")
    print(f"report_dir={report['report_dir']}")


if __name__ == "__main__":
    main()

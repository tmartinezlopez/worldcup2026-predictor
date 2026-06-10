"""Print a compact smoke summary from PostgreSQL."""

from __future__ import annotations

import argparse
from pathlib import Path

from sqlalchemy import func, inspect, select
from sqlalchemy.orm import Session

from src.db.connection import get_session
from src.db.models import (
    Batch,
    BatchMatch,
    EvaluationResult,
    FeatureSet,
    Match,
    MatchFeature,
    ModelRun,
    Prediction,
    Team,
)

FINAL_REPORTS_ROOT = Path("data/processed/final_reports")


def get_smoke_summary(
    session: Session,
    *,
    batch_code: str,
) -> dict[str, int | str | None]:
    inspector = inspect(session.bind)
    existing_tables = set(inspector.get_table_names())
    table_models = {
        "teams": Team,
        "matches": Match,
        "batches": Batch,
        "batch_matches": BatchMatch,
        "feature_sets": FeatureSet,
        "match_features": MatchFeature,
        "model_runs": ModelRun,
        "predictions": Prediction,
        "evaluation_results": EvaluationResult,
    }

    summary: dict[str, int | str | None] = {}
    for table_name, model in table_models.items():
        if table_name not in existing_tables:
            summary[table_name] = 0
            continue
        summary[table_name] = int(
            session.scalar(select(func.count()).select_from(model)) or 0
        )

    if "predictions" in existing_tables:
        summary["official_predictions"] = int(
            session.scalar(
                select(func.count()).select_from(Prediction).where(
                    Prediction.is_official.is_(True)
                )
            )
            or 0
        )
        summary["frozen_predictions"] = int(
            session.scalar(
                select(func.count()).select_from(Prediction).where(
                    Prediction.is_frozen.is_(True)
                )
            )
            or 0
        )
    else:
        summary["official_predictions"] = 0
        summary["frozen_predictions"] = 0

    final_report_dir = FINAL_REPORTS_ROOT / batch_code
    html_path = final_report_dir / "batch_report.html"
    summary["latest_final_report_path"] = (
        str(html_path) if html_path.is_file() else None
    )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print final smoke summary")
    parser.add_argument("--batch-code", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with get_session() as session:
        summary = get_smoke_summary(session, batch_code=args.batch_code)

    ordered_keys = (
        "teams",
        "matches",
        "batches",
        "batch_matches",
        "feature_sets",
        "match_features",
        "model_runs",
        "predictions",
        "official_predictions",
        "frozen_predictions",
        "evaluation_results",
        "latest_final_report_path",
    )
    for key in ordered_keys:
        print(f"{key}: {summary.get(key)}")


if __name__ == "__main__":
    main()

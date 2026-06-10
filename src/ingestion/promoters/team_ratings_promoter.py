"""Controlled promotion of validated team ratings into the database."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.connection import get_session
from src.db.models import DataSource, ExternalTeamRating
from src.identity.team_identity import resolve_team_id
from src.staging.jsonl import read_jsonl


def _get_or_create_data_source(
    session: Session,
    source_name: str,
) -> DataSource:
    source = session.scalar(
        select(DataSource)
        .where(DataSource.name == source_name, DataSource.source_type == "team_ratings")
        .order_by(DataSource.id)
    )
    if source is not None:
        return source

    source = DataSource(name=source_name, source_type="team_ratings")
    session.add(source)
    session.flush()
    return source


def _build_promotion_report(
    *,
    run_dir: Path,
    dry_run: bool,
    rows_read: int,
    rows_promoted: int,
    rows_skipped: int,
    duplicates_skipped: int,
    unresolved_teams: list[dict],
    errors: list[str],
) -> dict:
    if errors:
        status = "failed"
    elif dry_run:
        status = "dry_run_passed"
    elif unresolved_teams:
        status = "needs_review"
    else:
        status = "promoted"

    return {
        "run_dir": str(run_dir),
        "entity_type": "team_ratings",
        "dry_run": dry_run,
        "promoted_at": datetime.now(UTC).isoformat(),
        "rows_read": rows_read,
        "rows_promoted": rows_promoted,
        "rows_skipped": rows_skipped,
        "duplicates_skipped": duplicates_skipped,
        "unresolved_teams": unresolved_teams,
        "errors": errors,
        "status": status,
    }


def _write_promotion_report(run_dir: Path, report: dict) -> None:
    (run_dir / "promotion_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    lines = [
        "# Promotion Report",
        "",
        f"- Status: `{report['status']}`",
        f"- Dry run: `{report['dry_run']}`",
        f"- Rows read: {report['rows_read']}",
        f"- Rows promoted: {report['rows_promoted']}",
        f"- Rows skipped: {report['rows_skipped']}",
        f"- Duplicates skipped: {report['duplicates_skipped']}",
        "",
        "## Unresolved Teams",
    ]
    if report["unresolved_teams"]:
        lines.extend(f"- {item}" for item in report["unresolved_teams"])
    else:
        lines.append("- None.")
    lines.extend(["", "## Errors"])
    if report["errors"]:
        lines.extend(f"- {error}" for error in report["errors"])
    else:
        lines.append("- None.")
    (run_dir / "promotion_report.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def promote_team_ratings(
    run_dir,
    session: Session,
    dry_run: bool = True,
) -> dict:
    run_dir = Path(run_dir)
    valid_path = run_dir / "valid.jsonl"
    validation_report_path = run_dir / "validation_report.json"
    if not validation_report_path.is_file():
        raise FileNotFoundError("validation_report.json is required before promotion")
    if not valid_path.is_file():
        raise FileNotFoundError("valid.jsonl is required before promotion")

    records = read_jsonl(valid_path)
    if not records:
        raise ValueError("valid.jsonl is empty; nothing to promote")

    rows_promoted = 0
    rows_skipped = 0
    duplicates_skipped = 0
    unresolved_teams: list[dict] = []
    errors: list[str] = []

    try:
        for index, record in enumerate(records, start=1):
            try:
                source = _get_or_create_data_source(session, record["source"])
                resolution = resolve_team_id(
                    session, record["team"], source_id=source.id
                )
                if not resolution.resolved or resolution.entity_id is None:
                    rows_skipped += 1
                    unresolved_teams.append(
                        {
                            "row_id": index,
                            "team": record["team"],
                            "source": record["source"],
                            "suggestions": [
                                suggestion.label
                                for suggestion in resolution.suggestions[:3]
                            ],
                        }
                    )
                    continue

                team_id = resolution.entity_id
                rating_date = date.fromisoformat(record["rating_date"])
                existing = session.scalar(
                    select(ExternalTeamRating)
                    .where(
                        ExternalTeamRating.team_id == team_id,
                        ExternalTeamRating.source_id == source.id,
                        ExternalTeamRating.rating_date == rating_date,
                    )
                    .order_by(ExternalTeamRating.id)
                )
                if existing is not None:
                    rows_skipped += 1
                    duplicates_skipped += 1
                    continue

                session.add(
                    ExternalTeamRating(
                        team_id=team_id,
                        source_id=source.id,
                        rating_date=rating_date,
                        rating_type=record.get("rating_type") or "team_rating_snapshot",
                        rating_value=record.get("rating_value"),
                        rank_value=record.get("rank_value"),
                    )
                )
                session.flush()
                rows_promoted += 1
            except Exception as exc:  # noqa: BLE001
                rows_skipped += 1
                errors.append(f"row {index}: {exc}")

        report = _build_promotion_report(
            run_dir=run_dir,
            dry_run=dry_run,
            rows_read=len(records),
            rows_promoted=rows_promoted,
            rows_skipped=rows_skipped,
            duplicates_skipped=duplicates_skipped,
            unresolved_teams=unresolved_teams,
            errors=errors,
        )

        if dry_run:
            session.rollback()
        else:
            session.commit()

        _write_promotion_report(run_dir, report)
        return report
    except Exception:  # noqa: BLE001
        session.rollback()
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Promote validated team ratings into the database"
    )
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--promote", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dry_run = not args.promote or args.dry_run
    with get_session() as session:
        report = promote_team_ratings(
            run_dir=args.run_dir,
            session=session,
            dry_run=dry_run,
        )
    print(report["status"])


if __name__ == "__main__":
    main()

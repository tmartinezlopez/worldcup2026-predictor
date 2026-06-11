"""Assign World Cup fixtures into dynamic batches by date and stage."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, time, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.connection import get_session
from src.db.models import Batch, BatchMatch, Competition, Match

REPORTS_ROOT = Path("data/processed/batch_assignment_reports")


def _stage_category(stage: str | None) -> str:
    if stage and "group" in stage.casefold():
        return "GROUP_STAGE"
    return "KNOCKOUT"


def _batch_code_for_match(match: Match) -> str:
    if match.date is None:
        raise ValueError("scheduled match is missing date")
    return f"{_stage_category(match.stage)}_{match.date.strftime('%Y%m%d')}"


def _first_match_start(match: Match) -> datetime:
    if match.date is None:
        raise ValueError("scheduled match is missing date")
    return datetime.combine(match.date, match.kickoff_time or time.min, tzinfo=UTC)


def _write_report(report_root: Path, report: dict) -> Path:
    report_dir = report_root / report["report_key"]
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "batch_assignment_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    lines = [
        "# Batch Assignment Report",
        "",
        f"- Competition: `{report['competition']}`",
        f"- Dry run: `{report['dry_run']}`",
        f"- Batches created: {report['batches_created']}",
        f"- Matches assigned: {report['matches_assigned']}",
        f"- Matches skipped: {report['matches_skipped']}",
        "",
        "## Batch Codes",
    ]
    if report["batch_codes"]:
        lines.extend(f"- `{code}`" for code in report["batch_codes"])
    else:
        lines.append("- None.")
    lines.extend(["", "## Warnings"])
    if report["warnings"]:
        lines.extend(f"- {warning}" for warning in report["warnings"])
    else:
        lines.append("- None.")
    (report_dir / "batch_assignment_report.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    return report_dir


def assign_worldcup_batches(
    session: Session,
    *,
    competition_name: str,
    dry_run: bool = True,
    report_root: Path | None = None,
) -> dict:
    competition = session.scalar(
        select(Competition)
        .where(Competition.name == competition_name)
        .order_by(Competition.id)
    )
    if competition is None:
        raise ValueError(f"unknown competition: {competition_name}")

    matches = session.scalars(
        select(Match)
        .where(
            Match.competition_id == competition.id,
            Match.status == "scheduled",
        )
        .order_by(Match.date, Match.kickoff_time, Match.id)
    ).all()
    if not matches:
        raise ValueError("no scheduled matches found for batch assignment")

    existing_batches = {
        batch.code: batch for batch in session.scalars(select(Batch).order_by(Batch.id))
    }
    existing_pairs = {
        (batch_match.batch_id, batch_match.match_id)
        for batch_match in session.scalars(select(BatchMatch)).all()
    }
    groups: dict[str, list[Match]] = {}
    for match in matches:
        groups.setdefault(_batch_code_for_match(match), []).append(match)

    batches_created = 0
    matches_assigned = 0
    matches_skipped = 0
    warnings: list[str] = []

    sorted_group_items = sorted(
        groups.items(),
        key=lambda item: min(_first_match_start(match) for match in item[1]),
    )
    for sequence_order, (batch_code, batch_matches) in enumerate(
        sorted_group_items, start=1
    ):
        batch = existing_batches.get(batch_code)
        first_start = min(_first_match_start(match) for match in batch_matches)
        cutoff_time = first_start - timedelta(minutes=10)
        stage_label = (
            "Group Stage"
            if batch_code.startswith("GROUP_STAGE")
            else "Knockout"
        )
        if batch is None:
            batch = Batch(
                code=batch_code,
                name=f"{stage_label} {batch_matches[0].date.isoformat()}",
                stage=stage_label,
                sequence_order=sequence_order,
                first_match_start=first_start,
                cutoff_time=cutoff_time,
                status="scheduled",
            )
            session.add(batch)
            session.flush()
            existing_batches[batch_code] = batch
            batches_created += 1
        else:
            if batch.first_match_start is None or first_start < batch.first_match_start:
                batch.first_match_start = first_start
                batch.cutoff_time = cutoff_time
                session.flush()

        ordered_matches = sorted(
            batch_matches, key=lambda match: (match.date, match.id)
        )
        for order_in_batch, match in enumerate(ordered_matches, start=1):
            pair = (batch.id, match.id)
            if pair in existing_pairs:
                matches_skipped += 1
                continue
            session.add(
                BatchMatch(
                    batch_id=batch.id,
                    match_id=match.id,
                    order_in_batch=order_in_batch,
                )
            )
            session.flush()
            existing_pairs.add(pair)
            matches_assigned += 1

    report_key = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    report = {
        "report_key": report_key,
        "competition": competition_name,
        "dry_run": dry_run,
        "batches_created": batches_created,
        "matches_assigned": matches_assigned,
        "matches_skipped": matches_skipped,
        "batch_codes": [item[0] for item in sorted_group_items],
        "warnings": sorted(set(warnings)),
    }
    report_root = report_root or REPORTS_ROOT
    report_dir = _write_report(report_root, report)

    if dry_run:
        session.rollback()
    else:
        session.commit()

    report["report_dir"] = str(report_dir)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Assign scheduled World Cup fixtures to dynamic batches"
    )
    parser.add_argument("--competition", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--promote", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dry_run = not args.promote or args.dry_run
    with get_session() as session:
        report = assign_worldcup_batches(
            session,
            competition_name=args.competition,
            dry_run=dry_run,
        )
    print(f"matches_assigned={report['matches_assigned']}")
    print(f"report_dir={report['report_dir']}")


if __name__ == "__main__":
    main()

"""Controlled promotion of validated fixtures into the database."""

from __future__ import annotations

import argparse
from datetime import date, time
from pathlib import Path

from sqlalchemy.orm import Session

from src.db.connection import get_session
from src.db.models import Match
from src.ingestion.promotion.historical_results_promoter import (
    _resolve_or_create_team,
    find_existing_match,
    get_or_create_competition,
)
from src.ingestion.promotion.reports import (
    build_promotion_report,
    write_promotion_markdown,
    write_promotion_report,
)
from src.staging.jsonl import read_jsonl


def _parse_matchday(value: object) -> int | None:
    if value in (None, ""):
        return None
    return int(str(value).strip())


def _parse_kickoff_time(value: object) -> time | None:
    if value in (None, ""):
        return None
    return time.fromisoformat(str(value).strip())


def create_fixture_match(
    session: Session,
    record: dict,
    team_a_id: int,
    team_b_id: int,
    competition_id: int,
) -> Match:
    match = Match(
        competition_id=competition_id,
        stage=record.get("stage"),
        matchday=_parse_matchday(record.get("matchday")),
        date=date.fromisoformat(record["date"]),
        kickoff_time=_parse_kickoff_time(record.get("kickoff_time")),
        timezone=None,
        team_a_id=team_a_id,
        team_b_id=team_b_id,
        home_team_id=None,
        away_team_id=None,
        venue_id=None,
        neutral_site=bool(record.get("neutral_site", False)),
        status="scheduled",
        team_a_goals=None,
        team_b_goals=None,
        winner_team_id=None,
    )
    session.add(match)
    session.flush()
    return match


def promote_fixtures(
    run_dir,
    session: Session,
    dry_run: bool = True,
    allow_create_teams: bool = False,
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
    teams_created = 0
    competitions_created = 0
    matches_created = 0
    matches_updated = 0
    unresolved_teams: list[dict] = []
    errors: list[str] = []

    try:
        for index, record in enumerate(records, start=1):
            try:
                competition_name = record.get("competition") or "Unknown Competition"
                competition, competition_created = get_or_create_competition(
                    session, competition_name
                )
                if competition_created:
                    competitions_created += 1

                team_a_id, team_a_created = _resolve_or_create_team(
                    session, record["team_a"], allow_create_teams
                )
                team_b_id, team_b_created = _resolve_or_create_team(
                    session, record["team_b"], allow_create_teams
                )

                if team_a_id is None or team_b_id is None:
                    rows_skipped += 1
                    unresolved_teams.append(
                        {
                            "row_id": index,
                            "team_a": record["team_a"],
                            "team_b": record["team_b"],
                        }
                    )
                    continue

                teams_created += int(team_a_created) + int(team_b_created)

                existing_match = find_existing_match(
                    session,
                    date.fromisoformat(record["date"]),
                    team_a_id,
                    team_b_id,
                    competition.id,
                )
                if existing_match is not None:
                    rows_skipped += 1
                    continue

                create_fixture_match(
                    session,
                    record,
                    team_a_id,
                    team_b_id,
                    competition.id,
                )
                matches_created += 1
                rows_promoted += 1
            except Exception as exc:  # noqa: BLE001
                rows_skipped += 1
                errors.append(f"row {index}: {exc}")

        report = build_promotion_report(
            run_dir=str(run_dir),
            entity_type="fixtures",
            dry_run=dry_run,
            rows_read=len(records),
            rows_promoted=rows_promoted,
            rows_skipped=rows_skipped,
            teams_created=teams_created,
            competitions_created=competitions_created,
            matches_created=matches_created,
            matches_updated=matches_updated,
            unresolved_teams=unresolved_teams,
            errors=errors,
        )

        if dry_run:
            session.rollback()
        else:
            session.commit()

        write_promotion_report(run_dir, report)
        write_promotion_markdown(run_dir, report)
        return report
    except Exception:  # noqa: BLE001
        session.rollback()
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Promote validated fixtures into the database"
    )
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--promote", action="store_true")
    parser.add_argument("--allow-create-teams", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dry_run = not args.promote or args.dry_run
    with get_session() as session:
        report = promote_fixtures(
            run_dir=args.run_dir,
            session=session,
            dry_run=dry_run,
            allow_create_teams=args.allow_create_teams,
        )
    print(report["status"])


if __name__ == "__main__":
    main()

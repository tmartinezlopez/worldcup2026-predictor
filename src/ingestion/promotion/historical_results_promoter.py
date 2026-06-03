"""Controlled promotion of validated historical results into the database."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.connection import get_session
from src.db.models import Competition, Match, Team, TeamAlias
from src.identity.normalizers import normalize_team_name
from src.identity.team_identity import require_team_id
from src.ingestion.promotion.reports import (
    build_promotion_report,
    write_promotion_markdown,
    write_promotion_report,
)
from src.staging.jsonl import read_jsonl


def _infer_competition_type(name: str) -> tuple[str, bool]:
    lowered = name.lower()
    if "world cup" in lowered:
        return "world_cup", True
    if any(token in lowered for token in ("euro", "copa", "africa", "asian", "gold")):
        return "continental_tournament", True
    if "friendly" in lowered:
        return "friendly", False
    return "other", False


def get_or_create_competition(session: Session, name: str) -> tuple[Competition, bool]:
    competition = session.scalar(
        select(Competition).where(Competition.name == name).order_by(Competition.id)
    )
    if competition is not None:
        return competition, False

    competition_type, is_major = _infer_competition_type(name)
    competition = Competition(
        name=name,
        official_name=name,
        competition_type=competition_type,
        confederation=None,
        is_fifa_official=(competition_type == "world_cup"),
        is_major_tournament=is_major,
    )
    session.add(competition)
    session.flush()
    return competition, True


def find_existing_match(
    session: Session,
    match_date: date,
    team_a_id: int,
    team_b_id: int,
    competition_id: int,
) -> Match | None:
    return session.scalar(
        select(Match)
        .where(
            Match.date == match_date,
            Match.team_a_id == team_a_id,
            Match.team_b_id == team_b_id,
            Match.competition_id == competition_id,
        )
        .order_by(Match.id)
    )


def _winner_team_id(
    team_a_id: int, team_b_id: int, team_a_goals: int, team_b_goals: int
) -> int | None:
    if team_a_goals > team_b_goals:
        return team_a_id
    if team_b_goals > team_a_goals:
        return team_b_id
    return None


def _create_team_for_seed(session: Session, team_name: str) -> Team:
    short_name = team_name[:3].upper() if team_name else "UNK"
    team = Team(
        name=team_name,
        official_name=team_name,
        short_name=short_name,
        country_code="UNK",
        fifa_code=None,
        confederation="UNKNOWN",
        is_active=True,
    )
    session.add(team)
    session.flush()
    session.add(
        TeamAlias(
            team_id=team.id,
            source_id=None,
            alias=team_name,
            normalized_alias=normalize_team_name(team_name),
            language=None,
            confidence=1.0,
            is_approved=True,
        )
    )
    session.flush()
    return team


def _resolve_or_create_team(
    session: Session,
    team_name: str,
    allow_create_teams: bool,
) -> tuple[int | None, bool]:
    try:
        return require_team_id(session, team_name), False
    except ValueError:
        if not allow_create_teams:
            return None, False
        team = _create_team_for_seed(session, team_name)
        return team.id, True


def create_match_from_record(
    session: Session,
    record: dict,
    team_a_id: int,
    team_b_id: int,
    competition_id: int,
) -> Match:
    match_date = date.fromisoformat(record["date"])
    team_a_goals = int(record["team_a_goals"])
    team_b_goals = int(record["team_b_goals"])
    match = Match(
        competition_id=competition_id,
        stage=record.get("stage"),
        matchday=None,
        date=match_date,
        kickoff_time=None,
        timezone=None,
        team_a_id=team_a_id,
        team_b_id=team_b_id,
        home_team_id=None,
        away_team_id=None,
        venue_id=None,
        neutral_site=bool(record.get("neutral_site", False)),
        status="finished",
        team_a_goals=team_a_goals,
        team_b_goals=team_b_goals,
        winner_team_id=_winner_team_id(
            team_a_id, team_b_id, team_a_goals, team_b_goals
        ),
    )
    session.add(match)
    session.flush()
    return match


def promote_historical_results(
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
                competition, competition_created = get_or_create_competition(
                    session, record["competition"]
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
                match_date = date.fromisoformat(record["date"])
                existing_match = find_existing_match(
                    session,
                    match_date,
                    team_a_id,
                    team_b_id,
                    competition.id,
                )
                if existing_match is None:
                    create_match_from_record(
                        session,
                        record,
                        team_a_id,
                        team_b_id,
                        competition.id,
                    )
                    matches_created += 1
                    rows_promoted += 1
                    continue

                new_team_a_goals = int(record["team_a_goals"])
                new_team_b_goals = int(record["team_b_goals"])
                if (
                    existing_match.status == "finished"
                    and (
                        existing_match.team_a_goals != new_team_a_goals
                        or existing_match.team_b_goals != new_team_b_goals
                    )
                ):
                    existing_match.team_a_goals = new_team_a_goals
                    existing_match.team_b_goals = new_team_b_goals
                    existing_match.winner_team_id = _winner_team_id(
                        team_a_id,
                        team_b_id,
                        new_team_a_goals,
                        new_team_b_goals,
                    )
                    session.flush()
                    matches_updated += 1
                    rows_promoted += 1
                else:
                    rows_skipped += 1
            except Exception as exc:  # noqa: BLE001
                rows_skipped += 1
                errors.append(f"row {index}: {exc}")

        report = build_promotion_report(
            run_dir=str(run_dir),
            entity_type="historical_results",
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
        description="Promote validated historical results into the database"
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
        report = promote_historical_results(
            run_dir=args.run_dir,
            session=session,
            dry_run=dry_run,
            allow_create_teams=args.allow_create_teams,
        )
    print(report["status"])


if __name__ == "__main__":
    main()

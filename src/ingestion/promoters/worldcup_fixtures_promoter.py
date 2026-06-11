"""Controlled promotion of real-like World Cup 2026 fixtures into the database."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.connection import get_session
from src.db.models import Match, Venue, VenueAlias
from src.identity.normalizers import normalize_venue_name
from src.ingestion.promotion.historical_results_promoter import (
    _resolve_or_create_team,
    find_existing_match,
    get_or_create_competition,
)
from src.staging.jsonl import read_jsonl


def _find_or_create_venue(session: Session, record: dict) -> Venue | None:
    venue_name = record.get("venue")
    if not venue_name:
        return None

    normalized_name = normalize_venue_name(venue_name)
    existing_alias = session.scalar(
        select(VenueAlias)
        .where(VenueAlias.normalized_alias == normalized_name)
        .order_by(VenueAlias.id)
    )
    if existing_alias is not None:
        return session.get(Venue, existing_alias.venue_id)

    existing_venue = session.scalar(
        select(Venue)
        .where(
            Venue.name == venue_name,
            Venue.city == record.get("city"),
            Venue.country == record.get("country"),
        )
        .order_by(Venue.id)
    )
    if existing_venue is not None:
        return existing_venue

    venue = Venue(
        name=venue_name,
        official_name=venue_name,
        city=record.get("city"),
        country=record.get("country"),
        timezone=None,
    )
    session.add(venue)
    session.flush()
    session.add(
        VenueAlias(
            venue_id=venue.id,
            source_id=None,
            alias=venue_name,
            normalized_alias=normalized_name,
            confidence=1.0,
            is_approved=True,
        )
    )
    session.flush()
    return venue


def create_worldcup_fixture_match(
    session: Session,
    record: dict,
    team_a_id: int,
    team_b_id: int,
    competition_id: int,
) -> Match:
    venue = _find_or_create_venue(session, record)
    match = Match(
        competition_id=competition_id,
        stage=record.get("stage"),
        matchday=None,
        date=date.fromisoformat(record["match_date"]),
        kickoff_time=None,
        timezone=None,
        team_a_id=team_a_id,
        team_b_id=team_b_id,
        home_team_id=None,
        away_team_id=None,
        venue_id=None if venue is None else venue.id,
        neutral_site=True,
        status="scheduled",
        team_a_goals=None,
        team_b_goals=None,
        winner_team_id=None,
    )
    session.add(match)
    session.flush()
    return match


def _build_report(
    *,
    run_dir: Path,
    dry_run: bool,
    rows_read: int,
    rows_promoted: int,
    rows_skipped: int,
    teams_created: int,
    competitions_created: int,
    matches_created: int,
    unresolved_teams: list[dict],
    errors: list[str],
    warnings: list[str],
) -> dict:
    if errors:
        status = "failed"
    elif dry_run:
        status = "dry_run_passed"
    elif unresolved_teams or rows_skipped:
        status = "needs_review"
    else:
        status = "promoted"
    return {
        "run_dir": str(run_dir),
        "entity_type": "worldcup_fixtures",
        "dry_run": dry_run,
        "promoted_at": datetime.now(UTC).isoformat(),
        "rows_read": rows_read,
        "rows_promoted": rows_promoted,
        "rows_skipped": rows_skipped,
        "teams_created": teams_created,
        "competitions_created": competitions_created,
        "matches_created": matches_created,
        "unresolved_teams": unresolved_teams,
        "errors": errors,
        "warnings": warnings,
        "status": status,
    }


def _write_report(run_dir: Path, report: dict) -> None:
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
        f"- Teams created: {report['teams_created']}",
        f"- Competitions created: {report['competitions_created']}",
        f"- Matches created: {report['matches_created']}",
        "",
        "## Warnings",
    ]
    if report["warnings"]:
        lines.extend(f"- {warning}" for warning in report["warnings"])
    else:
        lines.append("- None.")
    lines.extend(["", "## Unresolved Teams"])
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


def promote_worldcup_fixtures(
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
    unresolved_teams: list[dict] = []
    errors: list[str] = []
    warnings: list[str] = []
    if allow_create_teams:
        warnings.append(
            "allow_create_teams is enabled for a dev/demo workflow; "
            "this must not be treated as production fixture promotion"
        )

    try:
        for index, record in enumerate(records, start=1):
            try:
                competition_name = record.get("competition") or "FIFA World Cup 2026"
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
                    date.fromisoformat(record["match_date"]),
                    team_a_id,
                    team_b_id,
                    competition.id,
                )
                if existing_match is not None:
                    if existing_match.status == "finished":
                        warnings.append(
                            "skipped fixture because a finished match already exists "
                            f"for row_id={index}"
                        )
                    rows_skipped += 1
                    continue

                create_worldcup_fixture_match(
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

        report = _build_report(
            run_dir=run_dir,
            dry_run=dry_run,
            rows_read=len(records),
            rows_promoted=rows_promoted,
            rows_skipped=rows_skipped,
            teams_created=teams_created,
            competitions_created=competitions_created,
            matches_created=matches_created,
            unresolved_teams=unresolved_teams,
            errors=errors,
            warnings=sorted(set(warnings)),
        )
        if dry_run:
            session.rollback()
        else:
            session.commit()
        _write_report(run_dir, report)
        return report
    except Exception:  # noqa: BLE001
        session.rollback()
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Promote validated World Cup 2026 fixtures into the database"
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
        report = promote_worldcup_fixtures(
            run_dir=args.run_dir,
            session=session,
            dry_run=dry_run,
            allow_create_teams=args.allow_create_teams,
        )
    print(report["status"])


if __name__ == "__main__":
    main()

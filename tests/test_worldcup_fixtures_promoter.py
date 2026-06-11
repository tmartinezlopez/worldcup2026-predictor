from datetime import date

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from src.db.base import Base
from src.db.models import Match, Team, TeamAlias, Venue
from src.identity.normalizers import normalize_team_name
from src.ingestion.promoters.worldcup_fixtures_promoter import (
    promote_worldcup_fixtures,
)
from src.staging.jsonl import write_jsonl


def _session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True)()


def _prepare_run_dir(tmp_path, records):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    write_jsonl(run_dir / "valid.jsonl", records)
    (run_dir / "validation_report.json").write_text("{}", encoding="utf-8")
    return run_dir


def _seed_team(session, name):
    team = Team(
        name=name,
        official_name=name,
        short_name=name[:3].upper(),
        country_code="UNK",
        fifa_code=None,
        confederation="UNKNOWN",
    )
    session.add(team)
    session.flush()
    session.add(
        TeamAlias(
            team_id=team.id,
            source_id=None,
            alias=name,
            normalized_alias=normalize_team_name(name),
            language=None,
            confidence=1.0,
            is_approved=True,
        )
    )
    session.flush()
    return team


def _record(team_a="Mexico", team_b="South Africa"):
    return {
        "match_date": "2026-06-11",
        "stage": "Group A",
        "group": "A",
        "team_a": team_a,
        "team_b": team_b,
        "venue": "Estadio Azteca",
        "city": "Mexico City",
        "country": "Mexico",
        "competition": "FIFA World Cup 2026",
        "source": "sample",
    }


def test_worldcup_promoter_dry_run_does_not_insert(tmp_path):
    session = _session()
    _seed_team(session, "Mexico")
    _seed_team(session, "South Africa")
    run_dir = _prepare_run_dir(tmp_path, [_record()])

    report = promote_worldcup_fixtures(run_dir, session, dry_run=True)

    assert report["rows_promoted"] == 1
    assert session.scalar(select(Match)) is None


def test_worldcup_promoter_inserts_scheduled_match(tmp_path):
    session = _session()
    _seed_team(session, "Mexico")
    _seed_team(session, "South Africa")
    run_dir = _prepare_run_dir(tmp_path, [_record()])

    report = promote_worldcup_fixtures(run_dir, session, dry_run=False)
    match = session.scalar(select(Match))

    assert report["matches_created"] == 1
    assert match is not None
    assert match.status == "scheduled"
    assert match.date == date.fromisoformat("2026-06-11")
    assert session.scalar(select(Venue)) is not None


def test_worldcup_promoter_unresolved_teams_do_not_create_by_default(tmp_path):
    session = _session()
    run_dir = _prepare_run_dir(tmp_path, [_record()])

    report = promote_worldcup_fixtures(run_dir, session, dry_run=False)

    assert report["rows_skipped"] == 1
    assert report["unresolved_teams"]
    assert session.scalar(select(Match)) is None


def test_worldcup_promoter_allow_create_teams_for_demo(tmp_path):
    session = _session()
    run_dir = _prepare_run_dir(tmp_path, [_record()])

    report = promote_worldcup_fixtures(
        run_dir,
        session,
        dry_run=False,
        allow_create_teams=True,
    )

    assert report["rows_promoted"] == 1
    assert report["teams_created"] == 2
    assert any("allow_create_teams" in warning for warning in report["warnings"])

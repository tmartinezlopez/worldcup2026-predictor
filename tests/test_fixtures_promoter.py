from datetime import date

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from src.db.base import Base
from src.db.models import Competition, Match, Team, TeamAlias
from src.identity.normalizers import normalize_team_name
from src.ingestion.promotion.fixtures_promoter import promote_fixtures
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


def test_dry_run_does_not_insert_matches(tmp_path):
    session = _session()
    _seed_team(session, "Spain")
    _seed_team(session, "Italy")
    run_dir = _prepare_run_dir(
        tmp_path,
        [
            {
                "date": "2026-06-12",
                "kickoff_time": "18:00",
                "team_a": "Spain",
                "team_b": "Italy",
                "competition": "Friendly",
                "stage": "Group Stage",
                "matchday": "1",
                "neutral_site": False,
            }
        ],
    )

    report = promote_fixtures(run_dir, session, dry_run=True)

    assert report["rows_promoted"] == 1
    assert session.scalar(select(Match)) is None


def test_promote_inserts_scheduled_match(tmp_path):
    session = _session()
    _seed_team(session, "Spain")
    _seed_team(session, "Italy")
    run_dir = _prepare_run_dir(
        tmp_path,
        [
            {
                "date": "2026-06-12",
                "kickoff_time": "18:00",
                "team_a": "Spain",
                "team_b": "Italy",
                "competition": "FIFA World Cup",
                "stage": "Group Stage",
                "matchday": "1",
                "neutral_site": True,
            }
        ],
    )

    report = promote_fixtures(run_dir, session, dry_run=False)
    match = session.scalar(select(Match))

    assert report["matches_created"] == 1
    assert match is not None
    assert match.status == "scheduled"
    assert match.matchday == 1


def test_unresolved_teams_are_skipped_without_allow_create(tmp_path):
    session = _session()
    run_dir = _prepare_run_dir(
        tmp_path,
        [
            {
                "date": "2026-06-12",
                "kickoff_time": "18:00",
                "team_a": "Spain",
                "team_b": "Italy",
                "competition": "FIFA World Cup",
                "stage": "Group Stage",
                "matchday": "1",
                "neutral_site": False,
            }
        ],
    )

    report = promote_fixtures(run_dir, session, dry_run=False)

    assert report["rows_skipped"] == 1
    assert report["unresolved_teams"]
    assert session.scalar(select(Match)) is None


def test_allow_create_teams_creates_teams_and_aliases(tmp_path):
    session = _session()
    run_dir = _prepare_run_dir(
        tmp_path,
        [
            {
                "date": "2026-06-12",
                "kickoff_time": "18:00",
                "team_a": "Spain",
                "team_b": "Italy",
                "competition": "FIFA World Cup",
                "stage": "Group Stage",
                "matchday": "1",
                "neutral_site": True,
            }
        ],
    )

    report = promote_fixtures(
        run_dir, session, dry_run=False, allow_create_teams=True
    )

    assert report["teams_created"] == 2
    assert session.scalar(select(Team)) is not None
    assert session.scalar(select(TeamAlias)) is not None


def test_no_duplicate_fixture_if_match_exists(tmp_path):
    session = _session()
    spain = _seed_team(session, "Spain")
    italy = _seed_team(session, "Italy")
    competition = Competition(
        name="FIFA World Cup",
        official_name="FIFA World Cup",
        competition_type="world_cup",
        confederation=None,
        is_fifa_official=True,
        is_major_tournament=True,
    )
    session.add(competition)
    session.flush()
    session.add(
        Match(
            competition_id=competition.id,
            stage="Group Stage",
            matchday=1,
            date=date.fromisoformat("2026-06-12"),
            team_a_id=spain.id,
            team_b_id=italy.id,
            neutral_site=True,
            status="scheduled",
        )
    )
    session.commit()
    run_dir = _prepare_run_dir(
        tmp_path,
        [
            {
                "date": "2026-06-12",
                "kickoff_time": "18:00",
                "team_a": "Spain",
                "team_b": "Italy",
                "competition": "FIFA World Cup",
                "stage": "Group Stage",
                "matchday": "1",
                "neutral_site": True,
            }
        ],
    )

    report = promote_fixtures(run_dir, session, dry_run=False)

    assert report["matches_created"] == 0
    assert report["rows_skipped"] == 1

from datetime import date

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from src.db.base import Base
from src.db.models import Competition, Match, Team, TeamAlias
from src.identity.normalizers import normalize_team_name
from src.ingestion.promotion.historical_results_promoter import (
    promote_historical_results,
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


def test_dry_run_does_not_insert_matches(tmp_path):
    session = _session()
    _seed_team(session, "Spain")
    _seed_team(session, "Italy")
    run_dir = _prepare_run_dir(
        tmp_path,
        [
            {
                "date": "2024-01-01",
                "team_a": "Spain",
                "team_b": "Italy",
                "team_a_goals": 2,
                "team_b_goals": 1,
                "competition": "Friendly",
                "stage": None,
                "neutral_site": False,
            }
        ],
    )

    report = promote_historical_results(run_dir, session, dry_run=True)

    assert report["rows_promoted"] == 1
    assert session.scalar(select(Match)) is None


def test_promote_inserts_match_with_preexisting_teams(tmp_path):
    session = _session()
    _seed_team(session, "Spain")
    italy = _seed_team(session, "Italy")
    run_dir = _prepare_run_dir(
        tmp_path,
        [
            {
                "date": "2024-01-01",
                "team_a": "Spain",
                "team_b": "Italy",
                "team_a_goals": 2,
                "team_b_goals": 1,
                "competition": "Friendly",
                "stage": None,
                "neutral_site": False,
            }
        ],
    )

    report = promote_historical_results(run_dir, session, dry_run=False)
    match = session.scalar(select(Match))

    assert report["matches_created"] == 1
    assert match is not None
    assert match.winner_team_id != italy.id


def test_unresolved_team_is_skipped(tmp_path):
    session = _session()
    _seed_team(session, "Spain")
    run_dir = _prepare_run_dir(
        tmp_path,
        [
            {
                "date": "2024-01-01",
                "team_a": "Spain",
                "team_b": "Unknown",
                "team_a_goals": 2,
                "team_b_goals": 1,
                "competition": "Friendly",
                "stage": None,
                "neutral_site": False,
            }
        ],
    )

    report = promote_historical_results(run_dir, session, dry_run=False)

    assert report["rows_skipped"] == 1
    assert report["unresolved_teams"]


def test_allow_create_teams_creates_teams_and_aliases(tmp_path):
    session = _session()
    run_dir = _prepare_run_dir(
        tmp_path,
        [
            {
                "date": "2024-01-01",
                "team_a": "Spain",
                "team_b": "Italy",
                "team_a_goals": 2,
                "team_b_goals": 1,
                "competition": "Friendly",
                "stage": None,
                "neutral_site": False,
            }
        ],
    )

    report = promote_historical_results(
        run_dir, session, dry_run=False, allow_create_teams=True
    )

    assert report["teams_created"] == 2
    assert session.scalar(select(Team)) is not None
    assert session.scalar(select(TeamAlias)) is not None


def test_no_duplicate_match_if_exists(tmp_path):
    session = _session()
    spain = _seed_team(session, "Spain")
    italy = _seed_team(session, "Italy")
    competition = Competition(
        name="Friendly",
        official_name="Friendly",
        competition_type="friendly",
        confederation=None,
        is_fifa_official=False,
        is_major_tournament=False,
    )
    session.add(competition)
    session.flush()
    session.add(
        Match(
            competition_id=competition.id,
            date=date.fromisoformat("2024-01-01"),
            team_a_id=spain.id,
            team_b_id=italy.id,
            neutral_site=False,
            status="finished",
            team_a_goals=2,
            team_b_goals=1,
            winner_team_id=spain.id,
        )
    )
    session.commit()
    run_dir = _prepare_run_dir(
        tmp_path,
        [
            {
                "date": "2024-01-01",
                "team_a": "Spain",
                "team_b": "Italy",
                "team_a_goals": 2,
                "team_b_goals": 1,
                "competition": "Friendly",
                "stage": None,
                "neutral_site": False,
            }
        ],
    )

    report = promote_historical_results(run_dir, session, dry_run=False)

    assert report["matches_created"] == 0
    assert report["rows_skipped"] == 1


def test_updates_existing_finished_match_score(tmp_path):
    session = _session()
    spain = _seed_team(session, "Spain")
    italy = _seed_team(session, "Italy")
    competition = Competition(
        name="Friendly",
        official_name="Friendly",
        competition_type="friendly",
        confederation=None,
        is_fifa_official=False,
        is_major_tournament=False,
    )
    session.add(competition)
    session.flush()
    match = Match(
        competition_id=competition.id,
        date=date.fromisoformat("2024-01-01"),
        team_a_id=spain.id,
        team_b_id=italy.id,
        neutral_site=False,
        status="finished",
        team_a_goals=0,
        team_b_goals=0,
        winner_team_id=None,
    )
    session.add(match)
    session.commit()
    run_dir = _prepare_run_dir(
        tmp_path,
        [
            {
                "date": "2024-01-01",
                "team_a": "Spain",
                "team_b": "Italy",
                "team_a_goals": 3,
                "team_b_goals": 1,
                "competition": "Friendly",
                "stage": None,
                "neutral_site": False,
            }
        ],
    )

    report = promote_historical_results(run_dir, session, dry_run=False)
    refreshed = session.scalar(select(Match))

    assert report["matches_updated"] == 1
    assert refreshed.team_a_goals == 3
    assert refreshed.winner_team_id == spain.id


def test_creates_competition_if_missing(tmp_path):
    session = _session()
    _seed_team(session, "Spain")
    _seed_team(session, "Italy")
    run_dir = _prepare_run_dir(
        tmp_path,
        [
            {
                "date": "2024-01-01",
                "team_a": "Spain",
                "team_b": "Italy",
                "team_a_goals": 2,
                "team_b_goals": 1,
                "competition": "World Cup",
                "stage": None,
                "neutral_site": False,
            }
        ],
    )

    report = promote_historical_results(run_dir, session, dry_run=False)

    assert report["competitions_created"] == 1
    assert session.scalar(select(Competition)) is not None


def test_promotion_report_contains_counts(tmp_path):
    session = _session()
    _seed_team(session, "Spain")
    _seed_team(session, "Italy")
    run_dir = _prepare_run_dir(
        tmp_path,
        [
            {
                "date": "2024-01-01",
                "team_a": "Spain",
                "team_b": "Italy",
                "team_a_goals": 2,
                "team_b_goals": 1,
                "competition": "Friendly",
                "stage": None,
                "neutral_site": False,
            }
        ],
    )

    report = promote_historical_results(run_dir, session, dry_run=False)

    assert report["rows_read"] == 1
    assert report["rows_promoted"] == 1

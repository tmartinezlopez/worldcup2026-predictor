from datetime import date

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from src.db.base import Base
from src.db.models import DataSource, ExternalTeamRating, Team, TeamAlias
from src.identity.normalizers import normalize_team_name
from src.ingestion.promoters.team_ratings_promoter import promote_team_ratings
from src.staging.jsonl import write_jsonl


def _session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True)()


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


def _prepare_run_dir(tmp_path, records):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    write_jsonl(run_dir / "valid.jsonl", records)
    (run_dir / "validation_report.json").write_text("{}", encoding="utf-8")
    return run_dir


def test_team_ratings_promoter_dry_run_does_not_insert(tmp_path):
    session = _session()
    _seed_team(session, "Spain")
    run_dir = _prepare_run_dir(
        tmp_path,
        [
            {
                "rating_date": "2026-06-10",
                "team": "Spain",
                "source": "fifa",
                "rating_type": "team_rating_snapshot",
                "rank_value": 3,
                "rating_value": 1854.10,
            }
        ],
    )

    report = promote_team_ratings(run_dir, session, dry_run=True)

    assert report["rows_promoted"] == 1
    assert session.scalar(select(ExternalTeamRating)) is None


def test_team_ratings_promoter_promotes_resolved_team(tmp_path):
    session = _session()
    team = _seed_team(session, "Spain")
    run_dir = _prepare_run_dir(
        tmp_path,
        [
            {
                "rating_date": "2026-06-10",
                "team": "Spain",
                "source": "fifa",
                "rating_type": "team_rating_snapshot",
                "rank_value": 3,
                "rating_value": 1854.10,
            }
        ],
    )

    report = promote_team_ratings(run_dir, session, dry_run=False)
    rating = session.scalar(select(ExternalTeamRating))
    source = session.scalar(select(DataSource))

    assert report["rows_promoted"] == 1
    assert rating is not None
    assert rating.team_id == team.id
    assert source is not None
    assert source.name == "fifa"


def test_team_ratings_promoter_does_not_create_unresolved_team(tmp_path):
    session = _session()
    run_dir = _prepare_run_dir(
        tmp_path,
        [
            {
                "rating_date": "2026-06-10",
                "team": "Unknown Team",
                "source": "fifa",
                "rating_type": "team_rating_snapshot",
                "rank_value": 33,
                "rating_value": 1500.0,
            }
        ],
    )

    report = promote_team_ratings(run_dir, session, dry_run=False)

    assert report["rows_skipped"] == 1
    assert report["unresolved_teams"]
    assert session.scalar(select(Team)) is None


def test_team_ratings_promoter_skips_duplicates(tmp_path):
    session = _session()
    team = _seed_team(session, "Spain")
    source = DataSource(name="fifa", source_type="team_ratings")
    session.add(source)
    session.flush()
    session.add(
        ExternalTeamRating(
            team_id=team.id,
            source_id=source.id,
            rating_date=date.fromisoformat("2026-06-10"),
            rating_type="team_rating_snapshot",
            rating_value=1854.10,
            rank_value=3,
        )
    )
    session.commit()
    run_dir = _prepare_run_dir(
        tmp_path,
        [
            {
                "rating_date": "2026-06-10",
                "team": "Spain",
                "source": "fifa",
                "rating_type": "team_rating_snapshot",
                "rank_value": 3,
                "rating_value": 1854.10,
            }
        ],
    )

    report = promote_team_ratings(run_dir, session, dry_run=False)

    assert report["duplicates_skipped"] == 1
    assert report["rows_promoted"] == 0

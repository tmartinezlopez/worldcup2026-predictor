from datetime import UTC, datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from src.db.base import Base
from src.db.models import Batch, BatchMatch, Competition, Match, Team
from src.ingestion.promoters.worldcup_batch_assigner import assign_worldcup_batches


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
    return team


def test_batch_assigner_creates_group_batch_and_cutoff(tmp_path):
    session = _session()
    team_a = _seed_team(session, "Mexico")
    team_b = _seed_team(session, "South Africa")
    competition = Competition(
        name="FIFA World Cup 2026",
        official_name="FIFA World Cup 2026",
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
            stage="Group A",
            matchday=None,
            date=datetime(2026, 6, 11, tzinfo=UTC).date(),
            kickoff_time=None,
            team_a_id=team_a.id,
            team_b_id=team_b.id,
            neutral_site=True,
            status="scheduled",
        )
    )
    session.commit()

    report = assign_worldcup_batches(
        session,
        competition_name="FIFA World Cup 2026",
        dry_run=False,
        report_root=tmp_path / "reports",
    )
    batch = session.scalar(select(Batch))
    batch_match = session.scalar(select(BatchMatch))

    assert report["matches_assigned"] == 1
    assert batch is not None
    assert batch.code == "GROUP_STAGE_20260611"
    assert batch.cutoff_time == datetime(2026, 6, 10, 23, 50)
    assert batch_match is not None
    assert (
        tmp_path
        / "reports"
        / report["report_key"]
        / "batch_assignment_report.json"
    ).is_file()


def test_batch_assigner_dry_run_does_not_write(tmp_path):
    session = _session()
    team_a = _seed_team(session, "France")
    team_b = _seed_team(session, "Brazil")
    competition = Competition(
        name="FIFA World Cup 2026",
        official_name="FIFA World Cup 2026",
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
            stage="Quarterfinal",
            matchday=None,
            date=datetime(2026, 7, 1, tzinfo=UTC).date(),
            kickoff_time=None,
            team_a_id=team_a.id,
            team_b_id=team_b.id,
            neutral_site=True,
            status="scheduled",
        )
    )
    session.commit()

    report = assign_worldcup_batches(
        session,
        competition_name="FIFA World Cup 2026",
        dry_run=True,
        report_root=tmp_path / "reports",
    )

    assert report["matches_assigned"] == 1
    assert session.scalar(select(Batch)) is None

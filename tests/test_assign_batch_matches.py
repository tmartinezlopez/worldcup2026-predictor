from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from src.db.assign_batch_matches import assign_batch_matches
from src.db.base import Base
from src.db.batch_seed import seed_batches
from src.db.models import Batch, BatchMatch, Competition, Match, Team


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


def test_assigns_match_to_batch_by_stage_and_matchday():
    session = _session()
    seed_batches(session)
    team_a = _seed_team(session, "Spain")
    team_b = _seed_team(session, "Italy")
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
    match = Match(
        competition_id=competition.id,
        stage="Group Stage",
        matchday=1,
        team_a_id=team_a.id,
        team_b_id=team_b.id,
        neutral_site=True,
        status="scheduled",
    )
    session.add(match)
    session.flush()

    result = assign_batch_matches(session)
    batch_match = session.scalar(select(BatchMatch))
    batch = session.get(Batch, batch_match.batch_id)

    assert result["assigned"] == 1
    assert batch.code == "GROUP_STAGE_MD1"


def test_does_not_duplicate_batch_match():
    session = _session()
    seed_batches(session)
    team_a = _seed_team(session, "Spain")
    team_b = _seed_team(session, "Italy")
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
    match = Match(
        competition_id=competition.id,
        stage="Group Stage",
        matchday=1,
        team_a_id=team_a.id,
        team_b_id=team_b.id,
        neutral_site=True,
        status="scheduled",
    )
    session.add(match)
    session.flush()

    first = assign_batch_matches(session)
    second = assign_batch_matches(session)

    assert first["assigned"] == 1
    assert second["assigned"] == 0
    assert len(session.scalars(select(BatchMatch)).all()) == 1

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from src.db.base import Base
from src.db.models import Match, Team


def _build_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True)()


def test_match_rejects_same_team_on_both_sides():
    session = _build_session()

    team = Team(
        name="Spain",
        official_name="Spain National Team",
        short_name="ESP",
        country_code="ESP",
        fifa_code="ESP",
        confederation="UEFA",
    )
    session.add(team)
    session.flush()

    session.add(
        Match(
            team_a_id=team.id,
            team_b_id=team.id,
            status="scheduled",
        )
    )

    try:
        session.commit()
    except IntegrityError:
        session.rollback()
    else:
        raise AssertionError("Expected team distinctness constraint to fail")


def test_match_rejects_negative_goals():
    session = _build_session()

    team_a = Team(
        name="Argentina",
        official_name="Argentina National Team",
        short_name="ARG",
        country_code="ARG",
        fifa_code="ARG",
        confederation="CONMEBOL",
    )
    team_b = Team(
        name="France",
        official_name="France National Team",
        short_name="FRA",
        country_code="FRA",
        fifa_code="FRA",
        confederation="UEFA",
    )
    session.add_all([team_a, team_b])
    session.flush()

    session.add(
        Match(
            team_a_id=team_a.id,
            team_b_id=team_b.id,
            status="finished",
            team_a_goals=-1,
            team_b_goals=2,
        )
    )

    try:
        session.commit()
    except IntegrityError:
        session.rollback()
    else:
        raise AssertionError("Expected non-negative goals constraint to fail")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.db.base import Base
from src.db.models import Club, Player, Team
from src.identity.player_identity import (
    add_player_alias,
    require_player_id,
    resolve_player_id,
)


def _build_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True)()


def _seed_player_identity(session):
    france = Team(
        name="France",
        official_name="France National Team",
        short_name="FRA",
        country_code="FRA",
        fifa_code="FRA",
        confederation="UEFA",
    )
    argentina = Team(
        name="Argentina",
        official_name="Argentina National Team",
        short_name="ARG",
        country_code="ARG",
        fifa_code="ARG",
        confederation="CONMEBOL",
    )
    real_madrid = Club(
        name="Real Madrid",
        official_name="Real Madrid CF",
        country="Spain",
        league="La Liga",
    )
    session.add_all([france, argentina, real_madrid])
    session.flush()

    player = Player(
        full_name="Kylian Mbappe",
        display_name="Kylian Mbappe",
        nationality_team_id=france.id,
    )
    session.add(player)
    session.flush()

    add_player_alias(
        session,
        player.id,
        "K. Mbappe",
        team_id_context=france.id,
        club_id_context=real_madrid.id,
        is_approved=True,
    )
    add_player_alias(
        session,
        player.id,
        "K. Mbappe",
        team_id_context=argentina.id,
        confidence=0.7,
        is_approved=True,
    )
    session.commit()
    return france, argentina, real_madrid, player


def test_resolve_player_id_with_team_context():
    session = _build_session()
    france, _, _, player = _seed_player_identity(session)

    result = resolve_player_id(session, "K. Mbappe", team_id_context=france.id)

    assert result.resolved is True
    assert result.entity_id == player.id


def test_resolve_player_id_partial_name_suggests_but_does_not_resolve():
    session = _build_session()
    france, _, _, _ = _seed_player_identity(session)

    result = resolve_player_id(session, "Mbappe", team_id_context=france.id)

    assert result.resolved is False
    assert result.suggestions


def test_require_player_id_raises_for_unknown_player():
    session = _build_session()
    france, _, _, _ = _seed_player_identity(session)

    try:
        require_player_id(session, "Unknown Player", team_id_context=france.id)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError for unresolved player")


def test_context_prioritizes_matching_alias():
    session = _build_session()
    _, argentina, _, player = _seed_player_identity(session)

    result = resolve_player_id(session, "K. Mbappe", team_id_context=argentina.id)

    assert result.resolved is True
    assert result.entity_id == player.id
    assert result.confidence == 0.7

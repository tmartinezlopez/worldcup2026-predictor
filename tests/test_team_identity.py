from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.db.base import Base
from src.db.models import DataSource, Team
from src.identity.team_identity import (
    add_team_alias,
    require_team_id,
    resolve_team_id,
)


def _build_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True)()


def _seed_team_identity(session):
    source = DataSource(name="Test Source", source_type="test")
    usa = Team(
        name="United States",
        official_name="United States of America",
        short_name="USA",
        country_code="USA",
        fifa_code="USA",
        confederation="CONCACAF",
    )
    korea = Team(
        name="South Korea",
        official_name="Korea Republic",
        short_name="KOR",
        country_code="KOR",
        fifa_code="KOR",
        confederation="AFC",
    )
    ivory = Team(
        name="Ivory Coast",
        official_name="Cote d'Ivoire",
        short_name="CIV",
        country_code="CIV",
        fifa_code="CIV",
        confederation="CAF",
    )
    session.add_all([source, usa, korea, ivory])
    session.flush()

    add_team_alias(session, usa.id, "USA", source_id=source.id, is_approved=True)
    add_team_alias(
        session,
        korea.id,
        "Korea Republic",
        source_id=source.id,
        is_approved=True,
    )
    session.commit()
    return source, usa, korea, ivory


def test_resolve_team_id_exact_alias():
    session = _build_session()
    _, usa, _, _ = _seed_team_identity(session)

    result = resolve_team_id(session, "USA")

    assert result.resolved is True
    assert result.entity_id == usa.id
    assert result.resolution_type == "exact_alias"


def test_resolve_team_id_second_alias():
    session = _build_session()
    _, _, korea, _ = _seed_team_identity(session)

    result = resolve_team_id(session, "Korea Republic")

    assert result.resolved is True
    assert result.entity_id == korea.id


def test_resolve_team_id_unknown_returns_suggestions_when_possible():
    session = _build_session()
    _seed_team_identity(session)

    result = resolve_team_id(session, "United State")

    assert result.resolved is False
    assert result.suggestions


def test_require_team_id_raises_for_unknown_team():
    session = _build_session()
    _seed_team_identity(session)

    try:
        require_team_id(session, "Unknown Team")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError for unresolved team")


def test_add_team_alias_creates_normalized_alias():
    session = _build_session()
    source, _, _, ivory = _seed_team_identity(session)

    alias = add_team_alias(
        session,
        ivory.id,
        "Côte d’Ivoire",
        source_id=source.id,
        is_approved=False,
    )

    assert alias.normalized_alias == "cote divoire"

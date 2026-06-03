from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.db.base import Base
from src.db.models import Batch, BatchMatch, Match, Player, Prediction, Team


def test_metadata_create_all_on_sqlite():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    table_names = set(Base.metadata.tables.keys())
    assert "teams" in table_names
    assert "matches" in table_names
    assert "predictions" in table_names


def test_can_create_core_related_entities():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, future=True)()

    team_a = Team(
        name="Spain",
        official_name="Spain National Team",
        short_name="ESP",
        country_code="ESP",
        fifa_code="ESP",
        confederation="UEFA",
    )
    team_b = Team(
        name="Brazil",
        official_name="Brazil National Team",
        short_name="BRA",
        country_code="BRA",
        fifa_code="BRA",
        confederation="CONMEBOL",
    )
    session.add_all([team_a, team_b])
    session.flush()

    player = Player(
        full_name="Player One",
        display_name="P. One",
        nationality_team_id=team_a.id,
    )
    match = Match(
        team_a_id=team_a.id,
        team_b_id=team_b.id,
        status="scheduled",
        neutral_site=True,
    )
    batch = Batch(
        code="R16-001",
        name="Round of 16 - Batch 1",
        stage="round_of_16",
        sequence_order=1,
        status="scheduled",
    )
    session.add_all([player, match, batch])
    session.flush()

    batch_match = BatchMatch(batch_id=batch.id, match_id=match.id, order_in_batch=1)
    prediction = Prediction(
        match_id=match.id,
        batch_id=batch.id,
        predicted_at=datetime.now(UTC),
        predicted_score_a=2,
        predicted_score_b=1,
        predicted_outcome="team_a_win",
        p_team_a_win_90=0.55,
        p_draw_90=0.25,
        p_team_b_win_90=0.20,
    )
    session.add_all([batch_match, prediction])
    session.commit()

    assert player.id is not None
    assert match.id is not None
    assert batch_match.batch_id == batch.id
    assert prediction.id is not None

from datetime import date

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from src.db.base import Base
from src.db.counts import get_table_counts
from src.db.models import Batch, BatchMatch, Competition, Match, Team, TeamAlias
from src.identity.normalizers import normalize_team_name


def test_get_table_counts_returns_expected_counts():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, future=True)()

    team_a = Team(
        name="Spain",
        official_name="Spain",
        short_name="SPA",
        country_code="ESP",
        fifa_code="ESP",
        confederation="UEFA",
    )
    team_b = Team(
        name="Italy",
        official_name="Italy",
        short_name="ITA",
        country_code="ITA",
        fifa_code="ITA",
        confederation="UEFA",
    )
    session.add_all([team_a, team_b])
    session.flush()
    session.add_all(
        [
            TeamAlias(
                team_id=team_a.id,
                source_id=None,
                alias="Spain",
                normalized_alias=normalize_team_name("Spain"),
                language=None,
                confidence=1.0,
                is_approved=True,
            ),
            TeamAlias(
                team_id=team_b.id,
                source_id=None,
                alias="Italy",
                normalized_alias=normalize_team_name("Italy"),
                language=None,
                confidence=1.0,
                is_approved=True,
            ),
        ]
    )
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
            team_a_id=team_a.id,
            team_b_id=team_b.id,
            neutral_site=False,
            status="finished",
            team_a_goals=1,
            team_b_goals=0,
            winner_team_id=team_a.id,
        )
    )
    batch = Batch(
        code="GROUP_STAGE_MD1",
        name="Group Stage - Matchday 1",
        stage="Group Stage",
        sequence_order=1,
        status="scheduled",
    )
    session.add(batch)
    session.commit()
    match = session.scalar(select(Match))
    session.add(BatchMatch(batch_id=batch.id, match_id=match.id, order_in_batch=1))
    session.commit()

    counts = get_table_counts(session)

    assert counts["teams"] == 2
    assert counts["team_aliases"] == 2
    assert counts["competitions"] == 1
    assert counts["matches"] == 1
    assert counts["batches"] == 1
    assert counts["batch_matches"] == 1

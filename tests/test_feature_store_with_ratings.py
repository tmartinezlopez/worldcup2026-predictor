from datetime import UTC, date, datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from src.db.base import Base
from src.db.models import (
    Batch,
    BatchMatch,
    Competition,
    DataSource,
    ExternalTeamRating,
    FeatureSet,
    Match,
    MatchFeature,
    Team,
)
from src.features.build_feature_store import build_feature_store


def _session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True)()


def _seed_team(session, name, code):
    team = Team(
        name=name,
        official_name=name,
        short_name=code,
        country_code=code,
        fifa_code=code,
        confederation="TEST",
    )
    session.add(team)
    session.flush()
    return team


def _seed_batch_match(session):
    team_a = _seed_team(session, "United States", "USA")
    team_b = _seed_team(session, "Mexico", "MEX")
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
        date=date.fromisoformat("2026-06-12"),
        kickoff_time=datetime.strptime("18:00", "%H:%M").time(),
        team_a_id=team_a.id,
        team_b_id=team_b.id,
        neutral_site=True,
        status="scheduled",
    )
    session.add(match)
    session.flush()
    batch = Batch(
        code="GROUP_STAGE_MD1",
        name="Group Stage - Matchday 1",
        stage="Group Stage",
        sequence_order=1,
        first_match_start=datetime(2026, 6, 12, 18, 0, tzinfo=UTC),
        cutoff_time=datetime(2026, 6, 12, 17, 50, tzinfo=UTC),
        status="scheduled",
    )
    session.add(batch)
    session.flush()
    session.add(BatchMatch(batch_id=batch.id, match_id=match.id, order_in_batch=1))
    session.commit()
    return team_a, team_b


def test_feature_store_includes_ratings_features(tmp_path):
    session = _session()
    team_a, team_b = _seed_batch_match(session)
    source = DataSource(name="fifa", source_type="team_ratings")
    session.add(source)
    session.flush()
    session.add_all(
        [
            ExternalTeamRating(
                team_id=team_a.id,
                source_id=source.id,
                rating_date=date.fromisoformat("2026-06-10"),
                rating_type="team_rating_snapshot",
                rating_value=1648.75,
                rank_value=16,
            ),
            ExternalTeamRating(
                team_id=team_b.id,
                source_id=source.id,
                rating_date=date.fromisoformat("2026-06-10"),
                rating_type="team_rating_snapshot",
                rating_value=1631.20,
                rank_value=18,
            ),
        ]
    )
    session.commit()

    report = build_feature_store(
        session=session,
        batch_code="GROUP_STAGE_MD1",
        report_root=tmp_path / "feature_reports",
    )
    feature_set = session.scalar(select(FeatureSet))
    prediction_feature = session.scalar(select(MatchFeature))

    assert feature_set is not None
    assert report["feature_set_id"] == feature_set.id
    assert prediction_feature.features_json["team_a_rank"] == 16
    assert prediction_feature.features_json["team_b_rank"] == 18
    assert prediction_feature.features_json["rank_diff"] == -2
    assert prediction_feature.features_json["rating_points_diff"] == 17.55


def test_feature_store_warns_but_does_not_break_without_ratings(tmp_path):
    session = _session()
    _seed_batch_match(session)

    report = build_feature_store(
        session=session,
        batch_code="GROUP_STAGE_MD1",
        report_root=tmp_path / "feature_reports",
    )
    prediction_feature = session.scalar(select(MatchFeature))

    assert prediction_feature.features_json["team_a_rank"] is None
    assert prediction_feature.features_json["rating_points_diff"] is None
    assert any("missing rating snapshot" in warning for warning in report["warnings"])

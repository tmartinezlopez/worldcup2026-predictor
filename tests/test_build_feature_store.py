from datetime import UTC, date, datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from src.db.base import Base
from src.db.models import (
    Batch,
    BatchMatch,
    Competition,
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


def test_build_feature_store_creates_training_and_prediction_rows(tmp_path):
    session = _session()
    team_a = _seed_team(session, "Spain", "ESP")
    team_b = _seed_team(session, "Italy", "ITA")
    team_c = _seed_team(session, "Brazil", "BRA")
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

    finished_before_cutoff = Match(
        competition_id=competition.id,
        stage="Friendly",
        matchday=None,
        date=date.fromisoformat("2026-06-01"),
        team_a_id=team_a.id,
        team_b_id=team_b.id,
        neutral_site=True,
        status="finished",
        team_a_goals=2,
        team_b_goals=1,
        winner_team_id=team_a.id,
    )
    finished_after_cutoff = Match(
        competition_id=competition.id,
        stage="Friendly",
        matchday=None,
        date=date.fromisoformat("2026-06-13"),
        team_a_id=team_b.id,
        team_b_id=team_c.id,
        neutral_site=True,
        status="finished",
        team_a_goals=1,
        team_b_goals=0,
        winner_team_id=team_b.id,
    )
    scheduled_batch_match = Match(
        competition_id=competition.id,
        stage="Group Stage",
        matchday=1,
        date=date.fromisoformat("2026-06-12"),
        team_a_id=team_a.id,
        team_b_id=team_c.id,
        neutral_site=True,
        status="scheduled",
    )
    session.add_all(
        [finished_before_cutoff, finished_after_cutoff, scheduled_batch_match]
    )
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
    session.add(
        BatchMatch(
            batch_id=batch.id,
            match_id=scheduled_batch_match.id,
            order_in_batch=1,
        )
    )
    session.commit()

    report = build_feature_store(
        session=session,
        batch_code="GROUP_STAGE_MD1",
        report_root=tmp_path / "feature_reports",
    )

    feature_set = session.scalar(select(FeatureSet))
    match_features = session.scalars(
        select(MatchFeature).order_by(MatchFeature.match_id)
    ).all()
    training_feature = next(
        item for item in match_features if item.match_id == finished_before_cutoff.id
    )
    prediction_feature = next(
        item for item in match_features if item.match_id == scheduled_batch_match.id
    )

    assert feature_set is not None
    assert feature_set.rows_count == 2
    assert feature_set.data_coverage_json["leakage_check_passed"] is True
    assert report["training_rows"] == 1
    assert report["prediction_rows"] == 1
    assert training_feature.target_result == "team_a_win"
    assert prediction_feature.target_result is None
    assert prediction_feature.features_json["team_b_goals_for_recent"] == 0
    assert not any(
        item.match_id == finished_after_cutoff.id for item in match_features
    )
    assert (
        tmp_path
        / "feature_reports"
        / str(feature_set.id)
        / "feature_report.json"
    ).is_file()
    assert (
        tmp_path / "feature_reports" / str(feature_set.id) / "feature_report.md"
    ).is_file()

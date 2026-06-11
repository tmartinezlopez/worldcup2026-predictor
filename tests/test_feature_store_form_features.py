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


def test_last_5_form_features_are_cutoff_aware_and_ignore_future_matches(tmp_path):
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

    session.add_all(
        [
            Match(
                competition_id=competition.id,
                stage="Friendly",
                date=date.fromisoformat("2026-06-01"),
                team_a_id=team_a.id,
                team_b_id=team_b.id,
                neutral_site=True,
                status="finished",
                team_a_goals=2,
                team_b_goals=0,
            ),
            Match(
                competition_id=competition.id,
                stage="Friendly",
                date=date.fromisoformat("2026-06-02"),
                team_a_id=team_c.id,
                team_b_id=team_a.id,
                neutral_site=True,
                status="finished",
                team_a_goals=1,
                team_b_goals=1,
            ),
            Match(
                competition_id=competition.id,
                stage="Friendly",
                date=date.fromisoformat("2026-06-03"),
                team_a_id=team_a.id,
                team_b_id=team_c.id,
                neutral_site=True,
                status="finished",
                team_a_goals=0,
                team_b_goals=1,
            ),
            Match(
                competition_id=competition.id,
                stage="Friendly",
                date=date.fromisoformat("2026-06-04"),
                team_a_id=team_b.id,
                team_b_id=team_a.id,
                neutral_site=True,
                status="finished",
                team_a_goals=1,
                team_b_goals=3,
            ),
            Match(
                competition_id=competition.id,
                stage="Friendly",
                date=date.fromisoformat("2026-06-05"),
                team_a_id=team_a.id,
                team_b_id=team_b.id,
                neutral_site=True,
                status="finished",
                team_a_goals=2,
                team_b_goals=2,
            ),
            Match(
                competition_id=competition.id,
                stage="Friendly",
                date=date.fromisoformat("2026-06-06"),
                team_a_id=team_c.id,
                team_b_id=team_a.id,
                neutral_site=True,
                status="finished",
                team_a_goals=0,
                team_b_goals=1,
            ),
            Match(
                competition_id=competition.id,
                stage="Friendly",
                date=date.fromisoformat("2026-06-13"),
                team_a_id=team_a.id,
                team_b_id=team_b.id,
                neutral_site=True,
                status="finished",
                team_a_goals=5,
                team_b_goals=0,
            ),
        ]
    )
    session.flush()

    scheduled = Match(
        competition_id=competition.id,
        stage="Group Stage",
        date=date.fromisoformat("2026-06-12"),
        kickoff_time=datetime.strptime("18:00", "%H:%M").time(),
        team_a_id=team_a.id,
        team_b_id=team_b.id,
        neutral_site=True,
        status="scheduled",
    )
    session.add(scheduled)
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
    session.add(BatchMatch(batch_id=batch.id, match_id=scheduled.id, order_in_batch=1))
    session.commit()

    report = build_feature_store(
        session=session,
        batch_code="GROUP_STAGE_MD1",
        report_root=tmp_path / "feature_reports",
    )

    feature_set = session.scalar(select(FeatureSet))
    prediction_row = session.scalars(
        select(MatchFeature).where(MatchFeature.target_result.is_(None))
    ).one()

    assert feature_set is not None
    assert prediction_row.features_json["team_a_matches_last_5"] == 5
    assert prediction_row.features_json["team_a_points_last_5"] == 8
    assert prediction_row.features_json["team_a_goals_for_last_5"] == 7
    assert prediction_row.features_json["team_a_goals_against_last_5"] == 5
    assert prediction_row.features_json["team_a_goal_diff_last_5"] == 2
    assert prediction_row.features_json["team_b_matches_last_5"] == 3
    assert prediction_row.features_json["team_b_points_last_5"] == 1
    assert prediction_row.features_json["team_b_goals_for_last_5"] == 3
    assert prediction_row.features_json["team_b_goals_against_last_5"] == 7
    assert prediction_row.features_json["team_b_goal_diff_last_5"] == -4
    assert prediction_row.features_json["points_last_5_diff"] == 7
    assert prediction_row.features_json["goal_diff_last_5_diff"] == 6
    assert report["historical_form_features_present"] is True
    assert report["rating_features_present"] is False
    assert feature_set.data_coverage_json["historical_form_features_present"] is True


def test_missing_form_history_defaults_to_zero_with_warning(tmp_path):
    session = _session()
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

    scheduled = Match(
        competition_id=competition.id,
        stage="Group Stage",
        date=date.fromisoformat("2026-06-12"),
        kickoff_time=datetime.strptime("18:00", "%H:%M").time(),
        team_a_id=team_a.id,
        team_b_id=team_b.id,
        neutral_site=True,
        status="scheduled",
    )
    session.add(scheduled)
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
    session.add(BatchMatch(batch_id=batch.id, match_id=scheduled.id, order_in_batch=1))
    session.commit()

    report = build_feature_store(
        session=session,
        batch_code="GROUP_STAGE_MD1",
        report_root=tmp_path / "feature_reports",
    )
    prediction_row = session.scalar(select(MatchFeature))

    assert prediction_row.features_json["team_a_matches_last_5"] == 0
    assert prediction_row.features_json["points_last_5_diff"] == 0
    assert any("missing historical form" in warning for warning in report["warnings"])

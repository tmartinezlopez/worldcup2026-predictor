from datetime import UTC, date, datetime

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from src.db.base import Base
from src.db.models import (
    Batch,
    Competition,
    FeatureSet,
    Match,
    MatchFeature,
    Prediction,
    Team,
)
from src.models.train_baseline import train_baseline_model
from src.prediction.generate_predictions import generate_predictions


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


def _seed_training_bundle(session):
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

    feature_set = FeatureSet(
        name="feature_store_GROUP_STAGE_MD1",
        version="v1",
        batch_id=batch.id,
        cutoff_time=batch.cutoff_time,
        feature_config_json={"recent_form_window_matches": 5},
        rows_count=0,
        data_coverage_json={},
    )
    session.add(feature_set)
    session.flush()

    finished_matches = [
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
            team_a_id=team_b.id,
            team_b_id=team_c.id,
            neutral_site=True,
            status="finished",
            team_a_goals=1,
            team_b_goals=1,
        ),
        Match(
            competition_id=competition.id,
            stage="Friendly",
            date=date.fromisoformat("2026-06-03"),
            team_a_id=team_c.id,
            team_b_id=team_a.id,
            neutral_site=True,
            status="finished",
            team_a_goals=3,
            team_b_goals=1,
        ),
        Match(
            competition_id=competition.id,
            stage="Friendly",
            date=date.fromisoformat("2026-06-04"),
            team_a_id=team_a.id,
            team_b_id=team_c.id,
            neutral_site=True,
            status="finished",
            team_a_goals=1,
            team_b_goals=0,
        ),
        Match(
            competition_id=competition.id,
            stage="Friendly",
            date=date.fromisoformat("2026-06-05"),
            team_a_id=team_b.id,
            team_b_id=team_a.id,
            neutral_site=True,
            status="finished",
            team_a_goals=0,
            team_b_goals=2,
        ),
    ]
    scheduled_match = Match(
        competition_id=competition.id,
        stage="Group Stage",
        date=date.fromisoformat("2026-06-12"),
        team_a_id=team_a.id,
        team_b_id=team_c.id,
        neutral_site=True,
        status="scheduled",
    )
    session.add_all([*finished_matches, scheduled_match])
    session.flush()

    feature_rows = [
        ("team_a_win", finished_matches[0], 7, 3, 2, 5, 4, -3, 6),
        ("draw", finished_matches[1], 4, 4, 4, 4, 0, 0, 0),
        ("team_a_win", finished_matches[2], 8, 5, 3, 4, 3, -1, 3),
        ("team_a_win", finished_matches[3], 6, 5, 2, 5, 1, -3, 3),
        ("team_b_win", finished_matches[4], 2, 8, 7, 2, -6, 5, -6),
        (None, scheduled_match, 6, 6, 2, 4, 0, -2, 1),
    ]
    for (
        target_result,
        match,
        gf_a,
        gf_b,
        ga_a,
        ga_b,
        gf_diff,
        ga_diff,
        form_diff,
    ) in feature_rows:
        session.add(
            MatchFeature(
                feature_set_id=feature_set.id,
                match_id=match.id,
                team_a_id=match.team_a_id,
                team_b_id=match.team_b_id,
                features_json={
                    "team_a_id": match.team_a_id,
                    "team_b_id": match.team_b_id,
                    "is_knockout": False,
                    "neutral_site": True,
                    "team_a_goals_for_recent": gf_a,
                    "team_b_goals_for_recent": gf_b,
                    "team_a_goals_against_recent": ga_a,
                    "team_b_goals_against_recent": ga_b,
                    "goals_for_recent_diff": gf_diff,
                    "goals_against_recent_diff": ga_diff,
                    "recent_form_points_diff": form_diff,
                },
                target_result=target_result,
            )
        )
    feature_set.rows_count = 6
    session.commit()
    return feature_set


def test_creates_draft_prediction_rows_from_model_run(tmp_path):
    session = _session()
    feature_set = _seed_training_bundle(session)
    training_report = train_baseline_model(
        session,
        feature_set_id=feature_set.id,
        model_type="majority",
        report_root=tmp_path / "model_reports",
    )

    report = generate_predictions(
        session,
        model_run_id=training_report["model_run_id"],
        report_root=tmp_path / "model_reports",
    )
    predictions = session.scalars(select(Prediction)).all()

    assert report["predictions_created"] == 1
    assert len(predictions) == 1


def test_does_not_create_official_or_frozen_predictions(tmp_path):
    session = _session()
    feature_set = _seed_training_bundle(session)
    training_report = train_baseline_model(
        session,
        feature_set_id=feature_set.id,
        model_type="logistic",
        report_root=tmp_path / "model_reports",
    )

    generate_predictions(
        session,
        model_run_id=training_report["model_run_id"],
        report_root=tmp_path / "model_reports",
    )
    prediction = session.scalar(select(Prediction))

    assert prediction.is_official is False
    assert prediction.is_frozen is False


def test_probabilities_are_valid(tmp_path):
    session = _session()
    feature_set = _seed_training_bundle(session)
    training_report = train_baseline_model(
        session,
        feature_set_id=feature_set.id,
        model_type="poisson",
        report_root=tmp_path / "model_reports",
    )

    generate_predictions(
        session,
        model_run_id=training_report["model_run_id"],
        report_root=tmp_path / "model_reports",
    )
    prediction = session.scalar(select(Prediction))

    total = (
        prediction.p_team_a_win_90
        + prediction.p_draw_90
        + prediction.p_team_b_win_90
    )
    assert total == pytest.approx(1.0, abs=1e-6)
    assert 0 <= prediction.p_team_a_win_90 <= 1
    assert 0 <= prediction.p_draw_90 <= 1
    assert 0 <= prediction.p_team_b_win_90 <= 1

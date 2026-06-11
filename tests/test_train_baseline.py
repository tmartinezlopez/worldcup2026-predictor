from datetime import UTC, date, datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from src.db.base import Base
from src.db.models import (
    Batch,
    Competition,
    FeatureSet,
    Match,
    MatchFeature,
    ModelRun,
    Team,
)
from src.models.train_baseline import train_baseline_model


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


def _seed_feature_set_with_rows(session):
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

    matches = [
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
        Match(
            competition_id=competition.id,
            stage="Group Stage",
            date=date.fromisoformat("2026-06-12"),
            team_a_id=team_a.id,
            team_b_id=team_c.id,
            neutral_site=True,
            status="scheduled",
        ),
    ]
    session.add_all(matches)
    session.flush()

    rows = [
        MatchFeature(
            feature_set_id=feature_set.id,
            match_id=matches[0].id,
            team_a_id=matches[0].team_a_id,
            team_b_id=matches[0].team_b_id,
            features_json={
                "team_a_id": team_a.id,
                "team_b_id": team_b.id,
                "is_knockout": False,
                "neutral_site": True,
                "team_a_goals_for_recent": 7,
                "team_b_goals_for_recent": 3,
                "team_a_goals_against_recent": 2,
                "team_b_goals_against_recent": 5,
                "goals_for_recent_diff": 4,
                "goals_against_recent_diff": -3,
                "recent_form_points_diff": 6,
                "rating_points_diff": 25.0,
                "rank_diff": -3,
                "points_last_5_diff": 6,
                "goal_diff_last_5_diff": 5,
                "team_a_rating_points": 1660.0,
                "team_b_rating_points": 1635.0,
                "team_a_points_last_5": 12,
                "team_b_points_last_5": 6,
            },
            target_result="team_a_win",
        ),
        MatchFeature(
            feature_set_id=feature_set.id,
            match_id=matches[1].id,
            team_a_id=matches[1].team_a_id,
            team_b_id=matches[1].team_b_id,
            features_json={
                "team_a_id": team_b.id,
                "team_b_id": team_c.id,
                "is_knockout": False,
                "neutral_site": True,
                "team_a_goals_for_recent": 4,
                "team_b_goals_for_recent": 4,
                "team_a_goals_against_recent": 4,
                "team_b_goals_against_recent": 4,
                "goals_for_recent_diff": 0,
                "goals_against_recent_diff": 0,
                "recent_form_points_diff": 0,
                "rating_points_diff": 0.0,
                "rank_diff": 0,
                "points_last_5_diff": 0,
                "goal_diff_last_5_diff": 0,
                "team_a_rating_points": 1600.0,
                "team_b_rating_points": 1600.0,
                "team_a_points_last_5": 7,
                "team_b_points_last_5": 7,
            },
            target_result="draw",
        ),
        MatchFeature(
            feature_set_id=feature_set.id,
            match_id=matches[2].id,
            team_a_id=matches[2].team_a_id,
            team_b_id=matches[2].team_b_id,
            features_json={
                "team_a_id": team_c.id,
                "team_b_id": team_a.id,
                "is_knockout": False,
                "neutral_site": True,
                "team_a_goals_for_recent": 8,
                "team_b_goals_for_recent": 5,
                "team_a_goals_against_recent": 3,
                "team_b_goals_against_recent": 4,
                "goals_for_recent_diff": 3,
                "goals_against_recent_diff": -1,
                "recent_form_points_diff": 3,
                "rating_points_diff": 15.0,
                "rank_diff": -2,
                "points_last_5_diff": 4,
                "goal_diff_last_5_diff": 3,
                "team_a_rating_points": 1640.0,
                "team_b_rating_points": 1625.0,
                "team_a_points_last_5": 9,
                "team_b_points_last_5": 5,
            },
            target_result="team_a_win",
        ),
        MatchFeature(
            feature_set_id=feature_set.id,
            match_id=matches[3].id,
            team_a_id=matches[3].team_a_id,
            team_b_id=matches[3].team_b_id,
            features_json={
                "team_a_id": team_a.id,
                "team_b_id": team_c.id,
                "is_knockout": False,
                "neutral_site": True,
                "team_a_goals_for_recent": 6,
                "team_b_goals_for_recent": 5,
                "team_a_goals_against_recent": 2,
                "team_b_goals_against_recent": 5,
                "goals_for_recent_diff": 1,
                "goals_against_recent_diff": -3,
                "recent_form_points_diff": 3,
                "rating_points_diff": 10.0,
                "rank_diff": -1,
                "points_last_5_diff": 3,
                "goal_diff_last_5_diff": 2,
                "team_a_rating_points": 1630.0,
                "team_b_rating_points": 1620.0,
                "team_a_points_last_5": 8,
                "team_b_points_last_5": 5,
            },
            target_result="team_a_win",
        ),
        MatchFeature(
            feature_set_id=feature_set.id,
            match_id=matches[4].id,
            team_a_id=matches[4].team_a_id,
            team_b_id=matches[4].team_b_id,
            features_json={
                "team_a_id": team_b.id,
                "team_b_id": team_a.id,
                "is_knockout": False,
                "neutral_site": True,
                "team_a_goals_for_recent": 2,
                "team_b_goals_for_recent": 8,
                "team_a_goals_against_recent": 7,
                "team_b_goals_against_recent": 2,
                "goals_for_recent_diff": -6,
                "goals_against_recent_diff": 5,
                "recent_form_points_diff": -6,
                "rating_points_diff": -30.0,
                "rank_diff": 4,
                "points_last_5_diff": -7,
                "goal_diff_last_5_diff": -6,
                "team_a_rating_points": 1590.0,
                "team_b_rating_points": 1620.0,
                "team_a_points_last_5": 2,
                "team_b_points_last_5": 9,
            },
            target_result="team_b_win",
        ),
        MatchFeature(
            feature_set_id=feature_set.id,
            match_id=matches[5].id,
            team_a_id=matches[5].team_a_id,
            team_b_id=matches[5].team_b_id,
            features_json={
                "team_a_id": team_a.id,
                "team_b_id": team_c.id,
                "is_knockout": False,
                "neutral_site": True,
                "team_a_goals_for_recent": 6,
                "team_b_goals_for_recent": 6,
                "team_a_goals_against_recent": 2,
                "team_b_goals_against_recent": 4,
                "goals_for_recent_diff": 0,
                "goals_against_recent_diff": -2,
                "recent_form_points_diff": 1,
                "rating_points_diff": 8.0,
                "rank_diff": -1,
                "points_last_5_diff": 2,
                "goal_diff_last_5_diff": 1,
                "team_a_rating_points": 1628.0,
                "team_b_rating_points": 1620.0,
                "team_a_points_last_5": 8,
                "team_b_points_last_5": 6,
            },
            target_result=None,
        ),
    ]
    session.add_all(rows)
    feature_set.rows_count = len(rows)
    session.commit()
    return feature_set


def test_creates_model_run_from_feature_set(tmp_path):
    session = _session()
    feature_set = _seed_feature_set_with_rows(session)

    report = train_baseline_model(
        session,
        feature_set_id=feature_set.id,
        model_type="majority",
        report_root=tmp_path / "model_reports",
    )

    model_run = session.scalar(select(ModelRun))

    assert model_run is not None
    assert model_run.feature_set_id == feature_set.id
    assert report["training_rows"] == 5
    assert (
        tmp_path / "model_reports" / str(model_run.id) / "model_report.json"
    ).is_file()


def test_records_metrics_json(tmp_path):
    session = _session()
    feature_set = _seed_feature_set_with_rows(session)

    report = train_baseline_model(
        session,
        feature_set_id=feature_set.id,
        model_type="logistic",
        report_root=tmp_path / "model_reports",
    )

    model_run = session.scalar(select(ModelRun))

    assert model_run.metrics_json["training_rows"] == 5
    assert "train_accuracy" in model_run.metrics_json
    assert report["metrics"]["prediction_rows_available"] == 1


def test_handles_insufficient_training_gracefully(tmp_path):
    session = _session()
    feature_set = _seed_feature_set_with_rows(session)
    session.query(MatchFeature).filter(
        MatchFeature.feature_set_id == feature_set.id
    ).delete()
    session.add(
        MatchFeature(
            feature_set_id=feature_set.id,
            match_id=1,
            team_a_id=1,
            team_b_id=2,
            features_json={
                "team_a_id": 1,
                "team_b_id": 2,
                "is_knockout": False,
                "neutral_site": True,
                "team_a_goals_for_recent": 5,
                "team_b_goals_for_recent": 1,
                "team_a_goals_against_recent": 2,
                "team_b_goals_against_recent": 4,
                "goals_for_recent_diff": 4,
                "goals_against_recent_diff": -2,
                "recent_form_points_diff": 3,
                "rating_points_diff": 12.0,
                "rank_diff": -1,
                "points_last_5_diff": 3,
                "goal_diff_last_5_diff": 2,
                "team_a_rating_points": 1620.0,
                "team_b_rating_points": 1608.0,
                "team_a_points_last_5": 8,
                "team_b_points_last_5": 5,
            },
            target_result="team_a_win",
        )
    )
    session.commit()

    report = train_baseline_model(
        session,
        feature_set_id=feature_set.id,
        model_type="logistic",
        report_root=tmp_path / "model_reports",
    )

    model_run = session.scalar(select(ModelRun))

    assert report["fallback_used"] is True
    assert model_run.metrics_json["fallback_used"] is True
    assert model_run.metrics_json["fallback_reason"] is not None


def test_model_report_includes_features_and_fallback_metadata(tmp_path):
    session = _session()
    feature_set = _seed_feature_set_with_rows(session)
    feature_set.data_coverage_json = {
        "data_quality_warnings": [
            "missing rating snapshot at or before cutoff for team_b_id=2"
        ]
    }
    session.commit()

    report = train_baseline_model(
        session,
        feature_set_id=feature_set.id,
        model_type="logistic",
        report_root=tmp_path / "model_reports",
    )

    model_run = session.scalar(select(ModelRun))

    assert "rating_points_diff" in report["features_used"]
    assert report["class_distribution"]["team_a_win"] == 3
    assert report["data_quality_warnings"] == [
        "missing rating snapshot at or before cutoff for team_b_id=2"
    ]
    assert model_run.features_used_json["features_used"] == report["features_used"]
    assert model_run.metrics_json["features_used"] == report["features_used"]

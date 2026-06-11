import json
from datetime import UTC, date, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.db.base import Base
from src.db.models import Batch, Competition, FeatureSet, Match, MatchFeature, Team
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


def test_model_report_keeps_features_used_after_prediction_generation(tmp_path):
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
        rows_count=6,
        data_coverage_json={
            "data_quality_warnings": ["missing historical form before cutoff"]
        },
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

    feature_rows = [
        ("team_a_win", 25.0, 6, 5, 1660.0, 1635.0, 12, 6),
        ("draw", 0.0, 0, 0, 1600.0, 1600.0, 7, 7),
        ("team_a_win", 15.0, 4, 3, 1640.0, 1625.0, 9, 5),
        ("team_a_win", 10.0, 3, 2, 1630.0, 1620.0, 8, 5),
        ("team_b_win", -30.0, -7, -6, 1590.0, 1620.0, 2, 9),
        (None, 8.0, 2, 1, 1628.0, 1620.0, 8, 6),
    ]
    for match, row in zip(matches, feature_rows, strict=True):
        (
            target_result,
            rating_points_diff,
            points_diff,
            goal_diff,
            a_rating,
            b_rating,
            a_points,
            b_points,
        ) = row
        session.add(
            MatchFeature(
                feature_set_id=feature_set.id,
                match_id=match.id,
                team_a_id=match.team_a_id,
                team_b_id=match.team_b_id,
                features_json={
                    "rating_points_diff": rating_points_diff,
                    "points_last_5_diff": points_diff,
                    "goal_diff_last_5_diff": goal_diff,
                    "team_a_rating_points": a_rating,
                    "team_b_rating_points": b_rating,
                    "team_a_points_last_5": a_points,
                    "team_b_points_last_5": b_points,
                },
                target_result=target_result,
            )
        )
    session.commit()

    train_report = train_baseline_model(
        session,
        feature_set_id=feature_set.id,
        model_type="logistic",
        report_root=tmp_path / "model_reports",
    )
    generate_predictions(
        session,
        model_run_id=train_report["model_run_id"],
        report_root=tmp_path / "model_reports",
    )

    report_path = (
        tmp_path
        / "model_reports"
        / str(train_report["model_run_id"])
        / "model_report.json"
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert "rating_points_diff" in report["features_used"]
    assert report["fallback_reason"] is None
    assert report["class_distribution"]["team_a_win"] == 3
    assert report["model_family"] == "logistic"
    assert report["data_quality_warnings"] == ["missing historical form before cutoff"]

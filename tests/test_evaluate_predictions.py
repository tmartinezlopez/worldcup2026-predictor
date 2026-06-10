from datetime import UTC, date, datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from src.db.base import Base
from src.db.models import (
    Batch,
    Competition,
    EvaluationResult,
    Match,
    ModelRun,
    Prediction,
    Team,
)
from src.evaluation.evaluate_predictions import evaluate_predictions


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


def _seed_model_run_bundle(session):
    team_a = _seed_team(session, "Spain", "ESP")
    team_b = _seed_team(session, "Italy", "ITA")
    competition = Competition(
        name="FIFA World Cup",
        official_name="FIFA World Cup",
        competition_type="world_cup",
        confederation=None,
        is_fifa_official=True,
        is_major_tournament=True,
    )
    batch = Batch(
        code="GROUP_STAGE_MD1",
        name="Group Stage - Matchday 1",
        stage="Group Stage",
        sequence_order=1,
        first_match_start=datetime(2026, 6, 12, 18, 0, tzinfo=UTC),
        cutoff_time=datetime(2026, 6, 12, 17, 50, tzinfo=UTC),
        status="scheduled",
    )
    session.add_all([competition, batch])
    session.flush()

    model_run = ModelRun(
        model_name="baseline_majority",
        model_version="phase13_mvp_v1",
        trained_at=datetime.now(UTC),
        feature_set_id=None,
    )
    session.add(model_run)
    session.flush()

    finished_match = Match(
        competition_id=competition.id,
        stage="Group Stage",
        date=date.fromisoformat("2026-06-12"),
        team_a_id=team_a.id,
        team_b_id=team_b.id,
        neutral_site=True,
        status="finished",
        team_a_goals=2,
        team_b_goals=1,
    )
    scheduled_match = Match(
        competition_id=competition.id,
        stage="Group Stage",
        date=date.fromisoformat("2026-06-13"),
        team_a_id=team_a.id,
        team_b_id=team_b.id,
        neutral_site=True,
        status="scheduled",
    )
    session.add_all([finished_match, scheduled_match])
    session.flush()

    session.add_all(
        [
            Prediction(
                match_id=finished_match.id,
                batch_id=batch.id,
                model_run_id=model_run.id,
                predicted_at=datetime.now(UTC),
                predicted_score_a=2,
                predicted_score_b=1,
                predicted_outcome="team_a_win",
                p_team_a_win_90=0.7,
                p_draw_90=0.2,
                p_team_b_win_90=0.1,
            ),
            Prediction(
                match_id=scheduled_match.id,
                batch_id=batch.id,
                model_run_id=model_run.id,
                predicted_at=datetime.now(UTC),
                predicted_score_a=1,
                predicted_score_b=1,
                predicted_outcome="draw",
                p_team_a_win_90=0.4,
                p_draw_90=0.3,
                p_team_b_win_90=0.3,
            ),
        ]
    )
    session.commit()
    return model_run


def test_creates_evaluation_result_and_calculates_metrics(tmp_path):
    session = _session()
    model_run = _seed_model_run_bundle(session)

    report = evaluate_predictions(
        session,
        model_run_id=model_run.id,
        report_root=tmp_path / "evaluation_reports",
    )

    evaluation_result = session.scalar(select(EvaluationResult))

    assert evaluation_result is not None
    assert report["evaluated_predictions"] == 1
    assert report["accuracy"] == 1.0
    assert report["mean_brier_score"] is not None
    assert report["mean_log_loss"] is not None


def test_skips_scheduled_with_warning(tmp_path):
    session = _session()
    model_run = _seed_model_run_bundle(session)

    report = evaluate_predictions(
        session,
        model_run_id=model_run.id,
        report_root=tmp_path / "evaluation_reports",
    )

    assert report["skipped_predictions"] == 1
    assert any("scheduled" in warning for warning in report["warnings"])


def test_creates_report_json_and_md(tmp_path):
    session = _session()
    model_run = _seed_model_run_bundle(session)

    report = evaluate_predictions(
        session,
        model_run_id=model_run.id,
        report_root=tmp_path / "evaluation_reports",
    )

    report_dir = (
        tmp_path / "evaluation_reports" / str(report["evaluation_result_ids"][0])
    )
    assert (report_dir / "evaluation_report.json").is_file()
    assert (report_dir / "evaluation_report.md").is_file()

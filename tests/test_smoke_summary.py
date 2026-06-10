from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.db.base import Base
from src.db.models import (
    Batch,
    BatchMatch,
    EvaluationResult,
    FeatureSet,
    Match,
    MatchFeature,
    ModelRun,
    Prediction,
    Team,
)
from src.orchestration.smoke_summary import get_smoke_summary


def _session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True)()


def test_smoke_summary_calculates_counts(monkeypatch, tmp_path):
    session = _session()
    team = Team(
        name="Spain",
        official_name="Spain",
        short_name="ESP",
        country_code="ESP",
        fifa_code="ESP",
        confederation="TEST",
    )
    batch = Batch(
        code="GROUP_STAGE_MD1",
        name="Group Stage - Matchday 1",
        stage="Group Stage",
        sequence_order=1,
        status="scheduled",
    )
    session.add_all([team, batch])
    session.flush()

    match = Match(
        team_a_id=team.id,
        team_b_id=team.id + 1,
        status="scheduled",
        neutral_site=True,
    )
    session.add(match)
    session.flush()

    batch_match = BatchMatch(batch_id=batch.id, match_id=match.id, order_in_batch=1)
    feature_set = FeatureSet(name="fs", version="v1", batch_id=batch.id)
    session.add_all([batch_match, feature_set])
    session.flush()

    match_feature = MatchFeature(
        feature_set_id=feature_set.id,
        match_id=match.id,
        team_a_id=match.team_a_id,
        team_b_id=match.team_b_id,
        features_json={"team_a_id": match.team_a_id, "team_b_id": match.team_b_id},
        target_result=None,
    )
    model_run = ModelRun(
        model_name="baseline_poisson",
        model_version="v1",
        trained_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
        feature_set_id=feature_set.id,
    )
    session.add_all([match_feature, model_run])
    session.flush()

    prediction = Prediction(
        match_id=match.id,
        batch_id=batch.id,
        model_run_id=model_run.id,
        feature_set_id=feature_set.id,
        predicted_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
        predicted_score_a=1,
        predicted_score_b=0,
        predicted_outcome="team_a_win",
        p_team_a_win_90=0.6,
        p_draw_90=0.2,
        p_team_b_win_90=0.2,
        is_official=True,
        is_frozen=True,
    )
    session.add(prediction)
    session.flush()

    evaluation_result = EvaluationResult(
        prediction_id=prediction.id,
        match_id=match.id,
        batch_id=batch.id,
        evaluated_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
        actual_score_a=1,
        actual_score_b=0,
        actual_outcome="team_a_win",
    )
    session.add(evaluation_result)
    session.commit()

    monkeypatch.setattr(
        "src.orchestration.smoke_summary.FINAL_REPORTS_ROOT",
        tmp_path / "final_reports",
    )

    summary = get_smoke_summary(session, batch_code="GROUP_STAGE_MD1")

    assert summary["teams"] == 1
    assert summary["matches"] == 1
    assert summary["batches"] == 1
    assert summary["batch_matches"] == 1
    assert summary["feature_sets"] == 1
    assert summary["match_features"] == 1
    assert summary["model_runs"] == 1
    assert summary["predictions"] == 1
    assert summary["official_predictions"] == 1
    assert summary["frozen_predictions"] == 1
    assert summary["evaluation_results"] == 1


def test_smoke_summary_does_not_break_without_final_report(monkeypatch, tmp_path):
    session = _session()
    monkeypatch.setattr(
        "src.orchestration.smoke_summary.FINAL_REPORTS_ROOT",
        tmp_path / "final_reports",
    )

    summary = get_smoke_summary(session, batch_code="GROUP_STAGE_MD1")

    assert summary["latest_final_report_path"] is None

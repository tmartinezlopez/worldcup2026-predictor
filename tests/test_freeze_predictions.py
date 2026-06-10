from datetime import UTC, date, datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from src.db.base import Base
from src.db.models import Batch, Competition, Match, ModelRun, Prediction, Team
from src.prediction.freeze_predictions import freeze_predictions


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


def _seed_freeze_bundle(session, cutoff_time):
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
        cutoff_time=cutoff_time,
        status="scheduled",
    )
    model_run = ModelRun(
        model_name="baseline_majority",
        model_version="phase13_mvp_v1",
        trained_at=datetime.now(UTC),
        feature_set_id=None,
    )
    other_model_run = ModelRun(
        model_name="baseline_logistic",
        model_version="phase13_mvp_v1",
        trained_at=datetime.now(UTC),
        feature_set_id=None,
    )
    session.add_all([competition, batch, model_run, other_model_run])
    session.flush()

    match = Match(
        competition_id=competition.id,
        stage="Group Stage",
        date=date.fromisoformat("2026-06-12"),
        team_a_id=team_a.id,
        team_b_id=team_b.id,
        neutral_site=True,
        status="scheduled",
    )
    session.add(match)
    session.flush()

    draft_prediction = Prediction(
        match_id=match.id,
        batch_id=batch.id,
        model_run_id=model_run.id,
        predicted_at=datetime.now(UTC),
        predicted_score_a=1,
        predicted_score_b=0,
        predicted_outcome="team_a_win",
        p_team_a_win_90=0.6,
        p_draw_90=0.2,
        p_team_b_win_90=0.2,
        is_official=False,
        is_frozen=False,
    )
    session.add(draft_prediction)
    session.commit()
    return model_run, other_model_run, batch, match, draft_prediction


def test_freezes_draft_before_cutoff(tmp_path):
    session = _session()
    model_run, _, batch, _, prediction = _seed_freeze_bundle(
        session,
        datetime(2026, 6, 12, 17, 50, tzinfo=UTC),
    )

    report = freeze_predictions(
        session,
        model_run_id=model_run.id,
        batch_code=batch.code,
        yes_freeze=True,
        report_root=tmp_path / "freeze_reports",
        now=datetime(2026, 6, 12, 17, 0, tzinfo=UTC),
    )
    refreshed = session.scalar(select(Prediction).where(Prediction.id == prediction.id))

    assert report["frozen_count"] == 1
    assert refreshed.is_official is True
    assert refreshed.is_frozen is True


def test_does_not_freeze_without_yes_freeze(tmp_path):
    session = _session()
    model_run, _, batch, _, prediction = _seed_freeze_bundle(
        session,
        datetime(2026, 6, 12, 17, 50, tzinfo=UTC),
    )

    report = freeze_predictions(
        session,
        model_run_id=model_run.id,
        batch_code=batch.code,
        yes_freeze=False,
        report_root=tmp_path / "freeze_reports",
        now=datetime(2026, 6, 12, 17, 0, tzinfo=UTC),
    )
    refreshed = session.scalar(select(Prediction).where(Prediction.id == prediction.id))

    assert report["frozen_count"] == 0
    assert refreshed.is_official is False
    assert refreshed.is_frozen is False


def test_does_not_freeze_if_official_exists_for_same_match(tmp_path):
    session = _session()
    model_run, other_model_run, batch, match, _ = _seed_freeze_bundle(
        session,
        datetime(2026, 6, 12, 17, 50, tzinfo=UTC),
    )
    session.add(
        Prediction(
            match_id=match.id,
            batch_id=batch.id,
            model_run_id=other_model_run.id,
            predicted_at=datetime.now(UTC),
            predicted_score_a=0,
            predicted_score_b=1,
            predicted_outcome="team_b_win",
            p_team_a_win_90=0.2,
            p_draw_90=0.2,
            p_team_b_win_90=0.6,
            is_official=True,
            is_frozen=True,
        )
    )
    session.commit()

    report = freeze_predictions(
        session,
        model_run_id=model_run.id,
        batch_code=batch.code,
        yes_freeze=True,
        report_root=tmp_path / "freeze_reports",
        now=datetime(2026, 6, 12, 17, 0, tzinfo=UTC),
    )

    draft = session.scalar(
        select(Prediction).where(Prediction.model_run_id == model_run.id)
    )
    assert report["frozen_count"] == 0
    assert draft.is_official is False
    assert draft.is_frozen is False


def test_does_not_freeze_after_cutoff_without_allow_flag(tmp_path):
    session = _session()
    model_run, _, batch, _, prediction = _seed_freeze_bundle(
        session,
        datetime(2026, 6, 12, 17, 50, tzinfo=UTC),
    )

    report = freeze_predictions(
        session,
        model_run_id=model_run.id,
        batch_code=batch.code,
        yes_freeze=True,
        report_root=tmp_path / "freeze_reports",
        now=datetime(2026, 6, 12, 18, 0, tzinfo=UTC),
    )
    refreshed = session.scalar(select(Prediction).where(Prediction.id == prediction.id))

    assert report["frozen_count"] == 0
    assert refreshed.is_official is False
    assert refreshed.is_frozen is False


def test_freezes_after_cutoff_with_allow_flag_and_writes_report(tmp_path):
    session = _session()
    model_run, _, batch, _, prediction = _seed_freeze_bundle(
        session,
        datetime(2026, 6, 12, 17, 50, tzinfo=UTC),
    )

    report = freeze_predictions(
        session,
        model_run_id=model_run.id,
        batch_code=batch.code,
        yes_freeze=True,
        allow_after_cutoff=True,
        report_root=tmp_path / "freeze_reports",
        now=datetime(2026, 6, 12, 18, 0, tzinfo=UTC),
    )
    refreshed = session.scalar(select(Prediction).where(Prediction.id == prediction.id))
    report_dir = tmp_path / "freeze_reports" / report["report_dir"].split("/")[-1]

    assert report["frozen_count"] == 1
    assert refreshed.is_official is True
    assert refreshed.is_frozen is True
    assert (report_dir / "freeze_report.json").is_file()
    assert (report_dir / "freeze_report.md").is_file()


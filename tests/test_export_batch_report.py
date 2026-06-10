import csv
import json
from datetime import UTC, date, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.db.base import Base
from src.db.models import (
    Batch,
    BatchMatch,
    Competition,
    Match,
    ModelRun,
    Prediction,
    Team,
)
from src.reporting.export_batch_report import export_batch_report


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


def _seed_batch_bundle(session):
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
    model_run = ModelRun(
        model_name="baseline_poisson",
        model_version="phase13_mvp_v1",
        trained_at=datetime.now(UTC),
        feature_set_id=None,
    )
    session.add_all([competition, batch, model_run])
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
    session.add(BatchMatch(batch_id=batch.id, match_id=match.id, order_in_batch=1))
    session.flush()
    return batch, model_run, match


def test_generates_md_html_csv_json(tmp_path):
    session = _session()
    batch, model_run, match = _seed_batch_bundle(session)
    session.add(
        Prediction(
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
            is_official=True,
            is_frozen=True,
            confidence_label="high",
        )
    )
    session.commit()

    report = export_batch_report(
        session,
        batch_code=batch.code,
        output_dir=tmp_path / "final_reports",
    )

    output_dir = tmp_path / "final_reports" / batch.code
    assert report["summary"]["predictions_included"] == 1
    assert (output_dir / "batch_report.md").is_file()
    assert (output_dir / "batch_report.html").is_file()
    assert (output_dir / "batch_report.json").is_file()
    assert (output_dir / "predictions.csv").is_file()


def test_official_only_excludes_drafts(tmp_path):
    session = _session()
    batch, model_run, match = _seed_batch_bundle(session)
    session.add(
        Prediction(
            match_id=match.id,
            batch_id=batch.id,
            model_run_id=model_run.id,
            predicted_at=datetime.now(UTC),
            predicted_score_a=1,
            predicted_score_b=1,
            predicted_outcome="draw",
            p_team_a_win_90=0.3,
            p_draw_90=0.4,
            p_team_b_win_90=0.3,
            is_official=False,
            is_frozen=False,
        )
    )
    session.commit()

    report = export_batch_report(
        session,
        batch_code=batch.code,
        official_only=True,
        output_dir=tmp_path / "final_reports",
    )

    assert report["summary"]["predictions_included"] == 0
    assert "no predictions" in report["warnings"][0]


def test_include_drafts_includes_drafts_if_no_officials(tmp_path):
    session = _session()
    batch, model_run, match = _seed_batch_bundle(session)
    session.add(
        Prediction(
            match_id=match.id,
            batch_id=batch.id,
            model_run_id=model_run.id,
            predicted_at=datetime.now(UTC),
            predicted_score_a=1,
            predicted_score_b=1,
            predicted_outcome="draw",
            p_team_a_win_90=0.3,
            p_draw_90=0.4,
            p_team_b_win_90=0.3,
            is_official=False,
            is_frozen=False,
            confidence_label="medium",
        )
    )
    session.commit()

    report = export_batch_report(
        session,
        batch_code=batch.code,
        include_drafts=True,
        output_dir=tmp_path / "final_reports",
    )

    assert report["summary"]["predictions_included"] == 1
    assert report["summary"]["draft_predictions"] == 1
    assert any("only draft predictions" in warning for warning in report["warnings"])


def test_prefer_official_over_draft_for_same_match(tmp_path):
    session = _session()
    batch, model_run, match = _seed_batch_bundle(session)
    session.add_all(
        [
            Prediction(
                match_id=match.id,
                batch_id=batch.id,
                model_run_id=model_run.id,
                predicted_at=datetime(2026, 6, 10, 10, 0, tzinfo=UTC),
                predicted_score_a=1,
                predicted_score_b=1,
                predicted_outcome="draw",
                p_team_a_win_90=0.3,
                p_draw_90=0.4,
                p_team_b_win_90=0.3,
                is_official=False,
                is_frozen=False,
                confidence_label="medium",
            ),
            Prediction(
                match_id=match.id,
                batch_id=batch.id,
                model_run_id=model_run.id,
                predicted_at=datetime(2026, 6, 10, 11, 0, tzinfo=UTC),
                predicted_score_a=2,
                predicted_score_b=1,
                predicted_outcome="team_a_win",
                p_team_a_win_90=0.6,
                p_draw_90=0.2,
                p_team_b_win_90=0.2,
                is_official=True,
                is_frozen=True,
                confidence_label="high",
            ),
        ]
    )
    session.commit()

    report = export_batch_report(
        session,
        batch_code=batch.code,
        include_drafts=True,
        output_dir=tmp_path / "final_reports",
    )

    included = report["predictions"][0]
    assert included["predicted_outcome"] == "team_a_win"
    assert included["is_official"] is True


def test_warnings_if_no_predictions(tmp_path):
    session = _session()
    batch, _, _ = _seed_batch_bundle(session)
    session.commit()

    report = export_batch_report(
        session,
        batch_code=batch.code,
        include_drafts=True,
        output_dir=tmp_path / "final_reports",
    )
    json_report = json.loads(
        (tmp_path / "final_reports" / batch.code / "batch_report.json").read_text(
            encoding="utf-8"
        )
    )
    with (tmp_path / "final_reports" / batch.code / "predictions.csv").open(
        encoding="utf-8",
        newline="",
    ) as handle:
        rows = list(csv.DictReader(handle))

    assert report["summary"]["predictions_included"] == 0
    assert any("no predictions" in warning for warning in report["warnings"])
    assert json_report["summary"]["predictions_included"] == 0
    assert rows == []

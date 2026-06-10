from datetime import UTC, date, datetime

import pytest
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
from src.simulation.monte_carlo import normalize_probability_triplet, simulate_batch


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


def _seed_batch_with_matches(session, *, include_second_match: bool = False):
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

    match_1 = Match(
        competition_id=competition.id,
        stage="Group Stage",
        date=date.fromisoformat("2026-06-12"),
        team_a_id=team_a.id,
        team_b_id=team_b.id,
        neutral_site=True,
        status="scheduled",
    )
    session.add(match_1)
    session.flush()
    session.add(BatchMatch(batch_id=batch.id, match_id=match_1.id, order_in_batch=1))

    match_2 = None
    if include_second_match:
        match_2 = Match(
            competition_id=competition.id,
            stage="Group Stage",
            date=date.fromisoformat("2026-06-13"),
            team_a_id=team_b.id,
            team_b_id=team_a.id,
            neutral_site=True,
            status="scheduled",
        )
        session.add(match_2)
        session.flush()
        session.add(
            BatchMatch(batch_id=batch.id, match_id=match_2.id, order_in_batch=2)
        )
    session.commit()
    return batch, model_run, match_1, match_2


def test_normalizes_probabilities():
    probabilities = normalize_probability_triplet(0.6, 0.2, 0.25)
    assert sum(probabilities) == pytest.approx(1.0)


def test_simulates_with_stable_seed(tmp_path):
    session = _session()
    batch, model_run, match, _ = _seed_batch_with_matches(session)
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
        )
    )
    session.commit()

    report_a = simulate_batch(
        session,
        batch_code=batch.code,
        runs=500,
        official_only=True,
        seed=42,
        output_dir=tmp_path / "simulation_reports_a",
    )
    report_b = simulate_batch(
        session,
        batch_code=batch.code,
        runs=500,
        official_only=True,
        seed=42,
        output_dir=tmp_path / "simulation_reports_b",
    )

    assert report_a["team_results"] == report_b["team_results"]


def test_generates_json_md_csv_and_expected_points_reasonable(tmp_path):
    session = _session()
    batch, model_run, match, _ = _seed_batch_with_matches(session)
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
        )
    )
    session.commit()

    report = simulate_batch(
        session,
        batch_code=batch.code,
        runs=1000,
        official_only=True,
        seed=42,
        output_dir=tmp_path / "simulation_reports",
    )

    batch_dir = tmp_path / "simulation_reports" / batch.code
    team_results = {row["team_name"]: row for row in report["team_results"]}
    assert (batch_dir / "simulation_report.json").is_file()
    assert (batch_dir / "simulation_report.md").is_file()
    assert (batch_dir / "simulation_results.csv").is_file()
    assert (
        team_results["Spain"]["expected_points"]
        > team_results["Italy"]["expected_points"]
    )
    assert team_results["Spain"]["expected_points"] == pytest.approx(2.0, abs=0.2)


def test_handles_missing_predictions_with_warnings(tmp_path):
    session = _session()
    batch, model_run, match_1, _match_2 = _seed_batch_with_matches(
        session,
        include_second_match=True,
    )
    session.add(
        Prediction(
            match_id=match_1.id,
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
        )
    )
    session.commit()

    report = simulate_batch(
        session,
        batch_code=batch.code,
        runs=100,
        official_only=True,
        seed=42,
        output_dir=tmp_path / "simulation_reports",
    )

    assert report["summary"]["matches_in_batch"] == 2
    assert report["summary"]["matches_simulated"] == 1
    assert any(
        "skipped because no eligible prediction" in warning
        for warning in report["warnings"]
    )


def test_official_only_excludes_drafts(tmp_path):
    session = _session()
    batch, model_run, match, _ = _seed_batch_with_matches(session)
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

    report = simulate_batch(
        session,
        batch_code=batch.code,
        runs=100,
        official_only=True,
        seed=42,
        output_dir=tmp_path / "simulation_reports",
    )

    assert report["summary"]["matches_simulated"] == 0


def test_include_drafts_allows_drafts(tmp_path):
    session = _session()
    batch, model_run, match, _ = _seed_batch_with_matches(session)
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

    report = simulate_batch(
        session,
        batch_code=batch.code,
        runs=100,
        include_drafts=True,
        seed=42,
        output_dir=tmp_path / "simulation_reports",
    )

    assert report["summary"]["matches_simulated"] == 1
    assert any("only draft predictions" in warning for warning in report["warnings"])

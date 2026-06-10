from pathlib import Path

import pytest

from src.orchestration.run_batch import run_batch


class DummySession:
    pass


def test_run_batch_executes_steps_in_order_and_creates_report(monkeypatch, tmp_path):
    calls = []

    def fake_build_feature_store(session, batch_code):
        assert isinstance(session, DummySession)
        calls.append(("build_feature_store", batch_code))
        return {
            "feature_set_id": 11,
            "report_dir": "data/processed/feature_reports/11",
        }

    def fake_train_baseline_model(session, feature_set_id, model_type):
        calls.append(("train_baseline", feature_set_id, model_type))
        return {
            "model_run_id": 22,
            "report_dir": "data/processed/model_reports/22",
            "fallback_used": False,
            "warnings": [],
        }

    def fake_generate_predictions(session, model_run_id):
        calls.append(("generate_predictions", model_run_id))
        return {
            "predictions_created": 3,
            "predictions_skipped": 0,
            "report_dir": "data/processed/model_reports/22",
            "warnings": [],
        }

    def fake_evaluate_predictions(session, model_run_id):
        calls.append(("evaluate_predictions", model_run_id))
        return {
            "evaluated_predictions": 0,
            "skipped_predictions": 3,
            "evaluation_result_ids": [],
            "report_dir": "data/processed/evaluation_reports/model_run_22_empty",
            "warnings": ["no finished predictions were available for evaluation"],
        }

    def fake_freeze_predictions(
        session,
        model_run_id,
        batch_code,
        yes_freeze,
        allow_after_cutoff,
    ):
        calls.append(
            (
                "freeze_predictions",
                model_run_id,
                batch_code,
                yes_freeze,
                allow_after_cutoff,
            )
        )
        return {
            "frozen_count": 3,
            "skipped_count": 0,
            "report_dir": (
                "data/processed/freeze_reports/"
                "GROUP_STAGE_MD1_20260610T100000Z"
            ),
            "reasons": [],
        }

    monkeypatch.setattr(
        "src.orchestration.run_batch.build_feature_store",
        fake_build_feature_store,
    )
    monkeypatch.setattr(
        "src.orchestration.run_batch.train_baseline_model",
        fake_train_baseline_model,
    )
    monkeypatch.setattr(
        "src.orchestration.run_batch.generate_predictions",
        fake_generate_predictions,
    )
    monkeypatch.setattr(
        "src.orchestration.run_batch.evaluate_predictions",
        fake_evaluate_predictions,
    )
    monkeypatch.setattr(
        "src.orchestration.run_batch.freeze_predictions",
        fake_freeze_predictions,
    )

    report = run_batch(
        DummySession(),
        batch_code="GROUP_STAGE_MD1",
        model_type="poisson",
        freeze=True,
        allow_after_cutoff=True,
        skip_evaluation=False,
        yes_run=True,
        report_root=tmp_path / "batch_runs",
    )

    assert calls == [
        ("build_feature_store", "GROUP_STAGE_MD1"),
        ("train_baseline", 11, "poisson"),
        ("generate_predictions", 22),
        ("evaluate_predictions", 22),
        ("freeze_predictions", 22, "GROUP_STAGE_MD1", True, True),
    ]
    assert report["feature_set_id"] == 11
    assert report["model_run_id"] == 22
    assert report["predictions_created"] == 3
    report_dir = Path(report["report_dir"])
    assert (report_dir / "batch_run_report.json").is_file()
    assert (report_dir / "batch_run_report.md").is_file()


def test_evaluation_with_zero_evaluated_does_not_break(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "src.orchestration.run_batch.build_feature_store",
        lambda session, batch_code: {
            "feature_set_id": 1,
            "report_dir": "feature",
        },
    )
    monkeypatch.setattr(
        "src.orchestration.run_batch.train_baseline_model",
        lambda session, feature_set_id, model_type: {
            "model_run_id": 2,
            "report_dir": "model",
            "fallback_used": False,
            "warnings": [],
        },
    )
    monkeypatch.setattr(
        "src.orchestration.run_batch.generate_predictions",
        lambda session, model_run_id: {
            "predictions_created": 1,
            "predictions_skipped": 0,
            "report_dir": "predictions",
            "warnings": [],
        },
    )
    monkeypatch.setattr(
        "src.orchestration.run_batch.evaluate_predictions",
        lambda session, model_run_id: {
            "evaluated_predictions": 0,
            "skipped_predictions": 1,
            "evaluation_result_ids": [],
            "report_dir": "evaluation",
            "warnings": ["no finished predictions were available for evaluation"],
        },
    )

    report = run_batch(
        DummySession(),
        batch_code="GROUP_STAGE_MD1",
        model_type="majority",
        freeze=False,
        allow_after_cutoff=False,
        skip_evaluation=False,
        yes_run=True,
        report_root=tmp_path / "batch_runs",
    )

    assert report["steps"]["evaluate_predictions"]["status"] == "completed"
    assert "no finished predictions" in report["warnings"][0]


def test_freeze_only_runs_with_flag(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(
        "src.orchestration.run_batch.build_feature_store",
        lambda session, batch_code: {
            "feature_set_id": 1,
            "report_dir": "feature",
        },
    )
    monkeypatch.setattr(
        "src.orchestration.run_batch.train_baseline_model",
        lambda session, feature_set_id, model_type: {
            "model_run_id": 2,
            "report_dir": "model",
            "fallback_used": False,
            "warnings": [],
        },
    )
    monkeypatch.setattr(
        "src.orchestration.run_batch.generate_predictions",
        lambda session, model_run_id: {
            "predictions_created": 1,
            "predictions_skipped": 0,
            "report_dir": "predictions",
            "warnings": [],
        },
    )
    monkeypatch.setattr(
        "src.orchestration.run_batch.evaluate_predictions",
        lambda session, model_run_id: {
            "evaluated_predictions": 0,
            "skipped_predictions": 1,
            "evaluation_result_ids": [],
            "report_dir": "evaluation",
            "warnings": [],
        },
    )

    def fake_freeze(*args, **kwargs):
        calls.append("freeze")
        return {
            "frozen_count": 1,
            "skipped_count": 0,
            "report_dir": "freeze",
            "reasons": [],
        }

    monkeypatch.setattr(
        "src.orchestration.run_batch.freeze_predictions",
        fake_freeze,
    )

    report = run_batch(
        DummySession(),
        batch_code="GROUP_STAGE_MD1",
        model_type="majority",
        freeze=False,
        allow_after_cutoff=False,
        skip_evaluation=False,
        yes_run=True,
        report_root=tmp_path / "batch_runs",
    )

    assert calls == []
    assert report["steps"]["freeze_predictions"]["status"] == "skipped"


def test_without_yes_run_fails_controlled_way():
    with pytest.raises(ValueError, match="--yes-run"):
        run_batch(
            DummySession(),
            batch_code="GROUP_STAGE_MD1",
            model_type="majority",
            freeze=False,
            allow_after_cutoff=False,
            skip_evaluation=False,
            yes_run=False,
        )

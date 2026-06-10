from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_prediction_scripts_exist():
    assert (ROOT / "scripts/evaluate_predictions.sh").is_file()
    assert (ROOT / "scripts/freeze_predictions.sh").is_file()


def test_prediction_scripts_call_expected_modules():
    evaluate_script = (ROOT / "scripts/evaluate_predictions.sh").read_text(
        encoding="utf-8"
    )
    freeze_script = (ROOT / "scripts/freeze_predictions.sh").read_text(
        encoding="utf-8"
    )

    assert "src.evaluation.evaluate_predictions" in evaluate_script
    assert "--model-run-id" in evaluate_script
    assert "src.prediction.freeze_predictions" in freeze_script
    assert "--batch-code" in freeze_script
    assert "--yes-freeze" in freeze_script

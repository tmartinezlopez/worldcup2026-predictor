from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_baseline_scripts_exist():
    assert (ROOT / "scripts/train_baseline_model.sh").is_file()
    assert (ROOT / "scripts/generate_predictions.sh").is_file()


def test_baseline_scripts_call_expected_modules():
    train_script = (ROOT / "scripts/train_baseline_model.sh").read_text(
        encoding="utf-8"
    )
    predict_script = (ROOT / "scripts/generate_predictions.sh").read_text(
        encoding="utf-8"
    )

    assert "src.models.train_baseline" in train_script
    assert "--feature-set-id" in train_script
    assert "src.prediction.generate_predictions" in predict_script
    assert "--model-run-id" in predict_script

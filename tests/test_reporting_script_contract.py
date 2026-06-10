from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_reporting_script_exists():
    assert (ROOT / "scripts/export_batch_report.sh").is_file()


def test_reporting_script_calls_expected_module_and_accepts_flags():
    content = (ROOT / "scripts/export_batch_report.sh").read_text(encoding="utf-8")

    assert "src.reporting.export_batch_report" in content
    assert "--batch-code" in content
    assert '"${@:2}"' in content

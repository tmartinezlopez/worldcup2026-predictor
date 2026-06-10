from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_run_batch_script_exists():
    assert (ROOT / "scripts/run_batch.sh").is_file()


def test_run_batch_script_calls_expected_module_and_flags():
    content = (ROOT / "scripts/run_batch.sh").read_text(encoding="utf-8")

    assert "src.orchestration.run_batch" in content
    assert "--yes-run" in content
    assert '"${@:3}"' in content

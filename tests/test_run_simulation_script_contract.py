from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_run_simulation_script_exists():
    assert (ROOT / "scripts/run_simulation.sh").is_file()


def test_run_simulation_script_calls_expected_module_and_accepts_flags():
    content = (ROOT / "scripts/run_simulation.sh").read_text(encoding="utf-8")

    assert "src.simulation.monte_carlo" in content
    assert "--batch-code" in content
    assert '"${@:2}"' in content

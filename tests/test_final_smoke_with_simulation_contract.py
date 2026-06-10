from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_final_smoke_with_simulation_script_exists():
    assert (ROOT / "scripts/final_smoke_with_simulation.sh").is_file()


def test_final_smoke_with_simulation_script_references_expected_flow():
    content = (ROOT / "scripts/final_smoke_with_simulation.sh").read_text(
        encoding="utf-8"
    )

    assert "final_smoke.sh" in content
    assert "run_simulation.sh" in content
    assert "export_batch_report.sh" in content
    assert "FINAL SMOKE WITH SIMULATION PASSED" in content

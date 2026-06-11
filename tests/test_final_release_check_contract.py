from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_final_release_check_script_exists():
    assert (ROOT / "scripts/final_release_check.sh").is_file()


def test_final_release_check_script_references_expected_flow():
    content = (ROOT / "scripts/final_release_check.sh").read_text(encoding="utf-8")

    assert "ruff check src tests" in content
    assert "pytest -q" in content
    assert "final_demo.sh" in content
    assert "worldcup2026_minimal_smoke.sh" in content
    assert "real_data_activation_report.sh" in content
    assert "FINAL RELEASE CHECK PASSED" in content
    assert "git commit" not in content
    assert "git push" not in content

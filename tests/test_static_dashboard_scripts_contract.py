from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_static_dashboard_script_exists_and_calls_module():
    script_path = ROOT / "scripts/build_static_dashboard.sh"
    content = script_path.read_text(encoding="utf-8")

    assert script_path.is_file()
    assert "src.dashboard.static_dashboard" in content
    assert "--batch-code" in content
    assert '"${@:2}"' in content


def test_final_demo_script_references_expected_flow():
    script_path = ROOT / "scripts/final_demo.sh"
    content = script_path.read_text(encoding="utf-8")

    assert script_path.is_file()
    assert "final_smoke_with_simulation.sh" in content
    assert "build_static_dashboard.sh" in content
    assert "show_final_artifacts.sh" in content
    assert "FINAL DEMO PASSED" in content


def test_show_final_artifacts_references_dashboard():
    content = (ROOT / "scripts/show_final_artifacts.sh").read_text(encoding="utf-8")

    assert "data/processed/dashboard" in content
    assert "dashboard_html" in content

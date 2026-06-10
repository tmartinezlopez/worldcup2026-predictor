from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_real_data_scripts_exist():
    assert (ROOT / "scripts/audit_real_historical_results.sh").is_file()
    assert (ROOT / "scripts/promote_latest_historical_results.sh").is_file()
    assert (ROOT / "scripts/real_data_smoke.sh").is_file()


def test_real_data_smoke_contains_success_message():
    content = (ROOT / "scripts/real_data_smoke.sh").read_text(encoding="utf-8")
    assert "REAL DATA SMOKE PASSED" in content


def test_real_data_scripts_reference_expected_flow_without_data_raw_writes():
    audit_script = (ROOT / "scripts/audit_real_historical_results.sh").read_text(
        encoding="utf-8"
    )
    promote_script = (
        ROOT / "scripts/promote_latest_historical_results.sh"
    ).read_text(encoding="utf-8")
    smoke_script = (ROOT / "scripts/real_data_smoke.sh").read_text(
        encoding="utf-8"
    )

    assert "historical_results_audit" in audit_script
    assert "promote_historical_results.sh" in promote_script
    assert "--allow-create-teams" not in promote_script
    assert "audit_real_historical_results.sh" in smoke_script
    assert "data/raw" not in audit_script
    assert "data/raw" not in promote_script
    assert "data/raw" not in smoke_script

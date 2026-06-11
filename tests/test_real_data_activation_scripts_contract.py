from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_activate_real_historical_data_script_exists_and_is_dry_run_first():
    script_path = ROOT / "scripts/activate_real_historical_data.sh"
    content = script_path.read_text(encoding="utf-8")

    assert script_path.is_file()
    assert "REAL DATA ACTIVATION DRY RUN PASSED" in content
    assert "promote_latest_historical_results.sh" in content
    assert "promote_latest_historical_results.sh --promote" in content
    assert "bash scripts/promote_latest_historical_results.sh --promote" in content
    assert (
        "\nbash scripts/promote_latest_historical_results.sh --promote\n"
        not in content
    )


def test_rebuild_with_current_data_script_exists_and_contains_success_message():
    script_path = ROOT / "scripts/rebuild_with_current_data.sh"
    content = script_path.read_text(encoding="utf-8")

    assert script_path.is_file()
    assert "REBUILD WITH CURRENT DATA PASSED" in content
    assert "build_feature_store.sh" in content
    assert "build_static_dashboard.sh" in content


def test_real_data_demo_script_exists_and_does_not_auto_promote():
    script_path = ROOT / "scripts/real_data_demo.sh"
    content = script_path.read_text(encoding="utf-8")

    assert script_path.is_file()
    assert "activate_real_historical_data.sh" in content
    assert (
        "Dry-run complete. Promote real data manually if reports look good."
        in content
    )
    assert "promote_latest_historical_results.sh --promote" in content
    assert "bash scripts/promote_latest_historical_results.sh --promote" in content

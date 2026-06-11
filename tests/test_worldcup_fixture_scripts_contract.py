from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_worldcup_fixture_scripts_exist():
    for relative_path in (
        "scripts/import_worldcup_fixtures.sh",
        "scripts/promote_worldcup_fixtures.sh",
        "scripts/assign_worldcup_batches.sh",
        "scripts/seed_worldcup2026_minimal_fixtures.sh",
        "scripts/worldcup2026_minimal_smoke.sh",
    ):
        assert (ROOT / relative_path).is_file()


def test_worldcup_fixture_scripts_call_expected_modules():
    assert "src.ingestion.importers.worldcup_fixtures_importer" in (
        ROOT / "scripts/import_worldcup_fixtures.sh"
    ).read_text(encoding="utf-8")
    assert "src.ingestion.promoters.worldcup_fixtures_promoter" in (
        ROOT / "scripts/promote_worldcup_fixtures.sh"
    ).read_text(encoding="utf-8")
    assert "src.ingestion.promoters.worldcup_batch_assigner" in (
        ROOT / "scripts/assign_worldcup_batches.sh"
    ).read_text(encoding="utf-8")


def test_worldcup_minimal_smoke_script_contains_expected_flow():
    content = (ROOT / "scripts/worldcup2026_minimal_smoke.sh").read_text(
        encoding="utf-8"
    )

    assert "seed_sample_historical_results.sh" in content
    assert "seed_sample_team_ratings.sh" in content
    assert "seed_worldcup2026_minimal_fixtures.sh" in content
    assert "run_batch.sh" in content
    assert "run_simulation.sh" in content
    assert "export_batch_report.sh" in content
    assert "WORLDCUP2026 MINIMAL SMOKE PASSED" in content

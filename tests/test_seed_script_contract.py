from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_seed_script_exists():
    assert (ROOT / "scripts/seed_sample_historical_results.sh").is_file()


def test_seed_script_references_expected_flow():
    content = (ROOT / "scripts/seed_sample_historical_results.sh").read_text(
        encoding="utf-8"
    )

    assert "historical_results_sample.csv" in content
    assert "--allow-create-teams" in content
    assert "db_counts" in content or "src.db.counts" in content

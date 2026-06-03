from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_seed_sample_fixtures_script_exists():
    script_path = ROOT / "scripts" / "seed_sample_fixtures.sh"
    assert script_path.is_file()


def test_seed_sample_fixtures_script_mentions_expected_flow():
    content = (ROOT / "scripts" / "seed_sample_fixtures.sh").read_text(
        encoding="utf-8"
    )

    assert "fixtures_sample.csv" in content
    assert "--allow-create-teams" in content
    assert "seed_batches" in content or "batch_seed" in content
    assert "assign_batch_matches" in content

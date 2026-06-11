from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_final_smoke_script_exists():
    assert (ROOT / "scripts/final_smoke.sh").is_file()


def test_final_smoke_script_contains_expected_steps():
    content = (ROOT / "scripts/final_smoke.sh").read_text(encoding="utf-8")

    assert "start_db.sh" in content
    assert "seed_sample_historical_results.sh" in content
    assert "seed_sample_fixtures.sh" in content
    assert "seed_sample_team_ratings.sh" in content
    assert "run_batch.sh" in content
    assert "export_batch_report.sh" in content
    assert "FINAL SMOKE PASSED" in content
    assert 'batch_code="${1:-GROUP_STAGE_MD1}"' in content
    assert 'model_type="${2:-poisson}"' in content

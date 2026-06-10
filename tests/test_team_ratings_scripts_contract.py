from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_team_ratings_scripts_exist():
    assert (ROOT / "scripts/import_team_ratings.sh").is_file()
    assert (ROOT / "scripts/promote_team_ratings.sh").is_file()
    assert (ROOT / "scripts/seed_sample_team_ratings.sh").is_file()


def test_team_ratings_scripts_call_expected_modules():
    import_script = (ROOT / "scripts/import_team_ratings.sh").read_text(
        encoding="utf-8"
    )
    promote_script = (ROOT / "scripts/promote_team_ratings.sh").read_text(
        encoding="utf-8"
    )
    seed_script = (ROOT / "scripts/seed_sample_team_ratings.sh").read_text(
        encoding="utf-8"
    )

    assert "src.ingestion.importers.team_ratings_importer" in import_script
    assert "src.ingestion.promoters.team_ratings_promoter" in promote_script
    assert "team_ratings_sample.csv" in seed_script
    assert "--promote" in seed_script

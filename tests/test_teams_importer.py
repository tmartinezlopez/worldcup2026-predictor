from src.ingestion.importers.teams_importer import normalize_team_record, run
from src.staging import paths


def test_normalize_team_record():
    record = normalize_team_record({"name": "France"})

    assert record["entity_type"] == "team"
    assert record["name"] == "France"


def test_teams_importer_creates_staging_outputs(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "STAGING_ROOT", tmp_path / "imports")
    input_path = tmp_path / "teams.csv"
    input_path.write_text("name\nFrance\n\n", encoding="utf-8")

    run_dir = run(input_path)

    assert (run_dir / "normalized.jsonl").is_file()
    assert (run_dir / "rejected.jsonl").is_file()

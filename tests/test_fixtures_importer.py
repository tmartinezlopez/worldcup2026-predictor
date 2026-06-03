from src.ingestion.importers.fixtures_importer import normalize_fixture_record, run
from src.staging import paths
from src.staging.jsonl import read_jsonl


def test_normalize_fixture_record():
    record = normalize_fixture_record(
        {"date": "2026-06-01", "team_a": "A", "team_b": "B"}
    )

    assert record["entity_type"] == "fixture"
    assert record["status"] == "scheduled"


def test_fixtures_importer_rejects_same_team_and_invalid_date(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "STAGING_ROOT", tmp_path / "imports")
    input_path = tmp_path / "fixtures.csv"
    input_path.write_text(
        "date,team_a,team_b\n2026-06-01,A,A\nbad-date,C,D\n",
        encoding="utf-8",
    )

    run_dir = run(input_path)
    rejected = read_jsonl(run_dir / "rejected.jsonl")

    assert len(rejected) == 2

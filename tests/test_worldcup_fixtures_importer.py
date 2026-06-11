from src.ingestion.importers.worldcup_fixtures_importer import (
    normalize_worldcup_fixture_record,
    run,
)
from src.staging import paths
from src.staging.jsonl import read_jsonl


def test_normalize_worldcup_fixture_record_defaults_fields():
    record = normalize_worldcup_fixture_record(
        {
            "match_date": "2026-06-11",
            "stage": "group",
            "group": "A",
            "team_a": "Mexico",
            "team_b": "South Africa",
        }
    )

    assert record["competition"] == "FIFA World Cup 2026"
    assert record["source"] == "local_csv"
    assert record["stage"] == "Group A"


def test_worldcup_fixtures_importer_creates_staging(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "STAGING_ROOT", tmp_path / "imports")
    input_path = tmp_path / "fixtures.csv"
    input_path.write_text(
        "match_date,stage,group,team_a,team_b,venue,city,country,competition,source\n"
        "2026-06-11,group,A,Mexico,South Africa,Azteca,Mexico City,"
        "Mexico,FIFA World Cup 2026,sample\n",
        encoding="utf-8",
    )

    run_dir = run(input_path)

    for name in (
        "normalized.jsonl",
        "valid.jsonl",
        "rejected.jsonl",
        "validation_report.json",
        "review_report.md",
        "metadata.json",
    ):
        assert (run_dir / name).is_file()


def test_invalid_date_is_rejected(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "STAGING_ROOT", tmp_path / "imports")
    input_path = tmp_path / "fixtures.csv"
    input_path.write_text(
        "match_date,stage,group,team_a,team_b,venue,city,country,competition,source\n"
        "bad-date,group,A,Mexico,South Africa,Azteca,Mexico City,"
        "Mexico,FIFA World Cup 2026,sample\n",
        encoding="utf-8",
    )

    run_dir = run(input_path)
    rejected = read_jsonl(run_dir / "rejected.jsonl")

    assert len(rejected) == 1

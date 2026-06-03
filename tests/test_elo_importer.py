from src.ingestion.importers.elo_importer import normalize_elo_record, run
from src.staging import paths
from src.staging.jsonl import read_jsonl


def test_normalize_elo_record():
    record = normalize_elo_record(
        {"rating_date": "2026-05-01", "team": "France", "elo": "2000"}
    )

    assert record["rating_type"] == "elo"
    assert record["rating_value"] == 2000.0


def test_elo_importer_requires_rating_fields(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "STAGING_ROOT", tmp_path / "imports")
    input_path = tmp_path / "elo.csv"
    input_path.write_text(
        "rating_date,team,elo\n2026-05-01,France,2000\nbad-date,Brazil,\n",
        encoding="utf-8",
    )

    run_dir = run(input_path)
    rejected = read_jsonl(run_dir / "rejected.jsonl")

    assert len(rejected) == 1

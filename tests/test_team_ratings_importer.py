from src.ingestion.importers.team_ratings_importer import (
    normalize_team_rating_record,
    run,
)
from src.staging import paths
from src.staging.jsonl import read_jsonl


def test_normalize_team_rating_record():
    record = normalize_team_rating_record(
        {
            "rating_date": "2026-06-10",
            "team": "Spain",
            "source": "FIFA",
            "rank": "3",
            "rating_points": "1854.10",
        }
    )

    assert record["source"] == "fifa"
    assert record["rank_value"] == 3
    assert record["rating_value"] == 1854.10


def test_team_ratings_importer_creates_staging(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "STAGING_ROOT", tmp_path / "imports")
    input_path = tmp_path / "team_ratings.csv"
    input_path.write_text(
        "rating_date,team,source,rank,rating_points\n"
        "2026-06-10,Spain,fifa,3,1854.10\n"
        "2026-06-10,Italy,fifa,,\n",
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

    valid = read_jsonl(run_dir / "valid.jsonl")
    rejected = read_jsonl(run_dir / "rejected.jsonl")

    assert len(valid) == 1
    assert len(rejected) == 1

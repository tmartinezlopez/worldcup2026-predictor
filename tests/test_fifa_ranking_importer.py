from src.ingestion.importers.fifa_ranking_importer import (
    normalize_fifa_ranking_record,
    run,
)
from src.staging import paths
from src.staging.jsonl import read_jsonl


def test_fifa_ranking_generates_rank_and_points_records():
    records = normalize_fifa_ranking_record(
        {
            "ranking_date": "2026-05-01",
            "team": "France",
            "fifa_rank": "2",
            "fifa_points": "1800.5",
        }
    )

    assert len(records) == 2


def test_fifa_ranking_accepts_only_one_metric():
    records = normalize_fifa_ranking_record(
        {"ranking_date": "2026-05-01", "team": "Brazil", "fifa_points": "1750.0"}
    )

    assert len(records) == 1
    assert records[0]["rating_type"] == "fifa_points"


def test_fifa_ranking_rejects_when_no_metric(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "STAGING_ROOT", tmp_path / "imports")
    input_path = tmp_path / "fifa.csv"
    input_path.write_text(
        "ranking_date,team,fifa_rank,fifa_points\n2026-05-01,France,,\n",
        encoding="utf-8",
    )

    run_dir = run(input_path)
    rejected = read_jsonl(run_dir / "rejected.jsonl")

    assert len(rejected) == 1

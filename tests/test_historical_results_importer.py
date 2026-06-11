from datetime import date, timedelta

from src.ingestion.importers.historical_results_importer import (
    _to_int_or_none,
    normalize_historical_result_record,
    run,
)
from src.staging import paths
from src.staging.jsonl import read_jsonl


def test_to_int_or_none_normalizes_common_missing_markers():
    assert _to_int_or_none("NA") is None
    assert _to_int_or_none("N/A") is None
    assert _to_int_or_none("") is None
    assert _to_int_or_none("  ") is None
    assert _to_int_or_none("null") is None
    assert _to_int_or_none(" 1 ") == 1
    assert _to_int_or_none(2) == 2


def test_historical_results_supports_home_away():
    record = normalize_historical_result_record(
        {
            "date": "2024-01-01",
            "home_team": "Spain",
            "away_team": "Italy",
            "home_score": "2",
            "away_score": "1",
            "tournament": "Friendly",
        }
    )

    assert record["team_a"] == "Spain"
    assert record["team_b"] == "Italy"


def test_historical_results_supports_team_a_team_b():
    record = normalize_historical_result_record(
        {
            "date": "2024-01-01",
            "team_a": "Spain",
            "team_b": "Italy",
            "team_a_goals": "2",
            "team_b_goals": "1",
            "competition": "Friendly",
        }
    )

    assert record["team_a_goals"] == 2
    assert record["team_b_goals"] == 1


def test_historical_results_marks_missing_scores_as_pending():
    record = normalize_historical_result_record(
        {
            "date": "2024-01-01",
            "home_team": "Spain",
            "away_team": "Italy",
            "home_score": "NA",
            "away_score": "N/A",
            "tournament": "Friendly",
        }
    )

    assert record["team_a_goals"] is None
    assert record["team_b_goals"] is None
    assert record["status"] == "pending"


def test_historical_results_rejects_negative_goals_future_and_same_team(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(paths, "STAGING_ROOT", tmp_path / "imports")
    future_date = (date.today() + timedelta(days=2)).isoformat()
    input_path = tmp_path / "results.csv"
    input_path.write_text(
        "date,home_team,away_team,home_score,away_score,tournament\n"
        f"{future_date},A,B,1,0,Friendly\n"
        "2024-01-01,C,C,1,1,Friendly\n"
        "2024-01-02,D,E,-1,0,Friendly\n",
        encoding="utf-8",
    )

    run_dir = run(input_path)
    rejected = read_jsonl(run_dir / "rejected.jsonl")

    assert len(rejected) == 3


def test_historical_results_handles_na_scores_without_crashing(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(paths, "STAGING_ROOT", tmp_path / "imports")
    input_path = tmp_path / "results.csv"
    input_path.write_text(
        "date,home_team,away_team,home_score,away_score,tournament\n"
        "2024-01-01,Spain,Italy,NA,NA,Friendly\n"
        "2024-01-02,Brazil,Argentina,2,1,Friendly\n",
        encoding="utf-8",
    )

    run_dir = run(input_path)
    valid = read_jsonl(run_dir / "valid.jsonl")
    rejected = read_jsonl(run_dir / "rejected.jsonl")
    review_report = (run_dir / "review_report.md").read_text(encoding="utf-8")
    validation_report = (run_dir / "validation_report.json").read_text(encoding="utf-8")

    assert len(valid) == 1
    assert len(rejected) == 1
    assert rejected[0]["record"]["status"] == "pending"
    assert "empty_value" in review_report
    assert '"empty_value"' in validation_report


def test_historical_results_sample_like_row_still_passes():
    record = normalize_historical_result_record(
        {
            "date": "2024-01-01",
            "home_team": "Spain",
            "away_team": "Italy",
            "home_score": "0",
            "away_score": "1",
            "tournament": "Friendly",
        }
    )

    assert record["team_a_goals"] == 0
    assert record["team_b_goals"] == 1
    assert record["status"] == "finished"

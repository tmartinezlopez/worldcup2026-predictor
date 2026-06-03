from datetime import date, timedelta

from src.ingestion.importers.historical_results_importer import (
    normalize_historical_result_record,
    run,
)
from src.staging import paths
from src.staging.jsonl import read_jsonl


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

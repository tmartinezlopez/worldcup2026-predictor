"""Importer for historical match results."""

from __future__ import annotations

from src.ingestion.importers.base import (
    load_records,
    normalize_bool,
    parse_cli_args,
    run_basic_import,
)
from src.ingestion.importers.validators import (
    check_distinct_teams,
    check_record_date,
    check_record_not_future,
)


def _to_int_or_none(value):
    if value in (None, ""):
        return None
    return int(value)


def normalize_historical_result_record(record: dict) -> dict:
    return {
        "entity_type": "historical_result",
        "date": (record.get("date") or "").strip(),
        "team_a": (record.get("team_a") or record.get("home_team") or "").strip(),
        "team_b": (record.get("team_b") or record.get("away_team") or "").strip(),
        "team_a_goals": _to_int_or_none(
            record.get("team_a_goals") or record.get("home_score")
        ),
        "team_b_goals": _to_int_or_none(
            record.get("team_b_goals") or record.get("away_score")
        ),
        "competition": (
            record.get("competition") or record.get("tournament") or ""
        ).strip(),
        "stage": (record.get("stage") or "").strip() or None,
        "city": (record.get("city") or "").strip() or None,
        "country": (record.get("country") or "").strip() or None,
        "neutral_site": normalize_bool(
            record.get("neutral") or record.get("neutral_site")
        ),
        "status": "finished",
    }


def run(input_path):
    normalized_records = [
        normalize_historical_result_record(record)
        for record in load_records(input_path)
    ]
    return run_basic_import(
        source_name="historical_results_importer",
        source_type="historical_results",
        input_path=input_path,
        normalized_records=normalized_records,
        required_fields=[
            "date",
            "team_a",
            "team_b",
            "team_a_goals",
            "team_b_goals",
            "competition",
        ],
        duplicate_key_fields=["date", "team_a", "team_b", "competition"],
        custom_checks=[
            check_distinct_teams,
            check_record_date,
            check_record_not_future,
        ],
    )


def main() -> None:
    args = parse_cli_args("historical_results_importer")
    run_dir = run(args.input)
    print(run_dir)


if __name__ == "__main__":
    main()

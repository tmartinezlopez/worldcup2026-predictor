"""Importer for scheduled fixtures."""

from __future__ import annotations

from src.ingestion.importers.base import (
    load_records,
    normalize_bool,
    parse_cli_args,
    run_basic_import,
)
from src.ingestion.importers.validators import check_distinct_teams, check_record_date


def normalize_fixture_record(record: dict) -> dict:
    return {
        "entity_type": "fixture",
        "date": (record.get("date") or "").strip(),
        "kickoff_time": (record.get("kickoff_time") or "").strip() or None,
        "team_a": (record.get("team_a") or record.get("home_team") or "").strip(),
        "team_b": (record.get("team_b") or record.get("away_team") or "").strip(),
        "competition": (record.get("competition") or "").strip() or None,
        "stage": (record.get("stage") or "").strip() or None,
        "matchday": (record.get("matchday") or "").strip() or None,
        "venue": (record.get("venue") or "").strip() or None,
        "city": (record.get("city") or "").strip() or None,
        "country": (record.get("country") or "").strip() or None,
        "neutral_site": normalize_bool(record.get("neutral_site")),
        "status": "scheduled",
    }


def run(input_path):
    normalized_records = [
        normalize_fixture_record(record) for record in load_records(input_path)
    ]
    return run_basic_import(
        source_name="fixtures_importer",
        source_type="fixtures",
        input_path=input_path,
        normalized_records=normalized_records,
        required_fields=["date", "team_a", "team_b"],
        duplicate_key_fields=["date", "team_a", "team_b"],
        custom_checks=[check_distinct_teams, check_record_date],
    )


def main() -> None:
    args = parse_cli_args("fixtures_importer")
    run_dir = run(args.input)
    print(run_dir)


if __name__ == "__main__":
    main()

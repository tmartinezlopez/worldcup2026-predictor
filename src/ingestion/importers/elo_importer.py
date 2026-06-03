"""Importer for Elo rating snapshots."""

from __future__ import annotations

from src.ingestion.importers.base import load_records, parse_cli_args, run_basic_import
from src.ingestion.importers.validators import check_record_date


def _to_float_or_none(value):
    if value in (None, ""):
        return None
    return float(value)


def normalize_elo_record(record: dict) -> dict:
    return {
        "entity_type": "external_team_rating",
        "rating_type": "elo",
        "rating_date": (record.get("rating_date") or record.get("date") or "").strip(),
        "team": (record.get("team") or "").strip(),
        "rating_value": _to_float_or_none(
            record.get("elo") or record.get("rating_value")
        ),
        "source": "elo",
    }


def run(input_path):
    normalized_records = [
        normalize_elo_record(record) for record in load_records(input_path)
    ]
    return run_basic_import(
        source_name="elo_importer",
        source_type="elo",
        input_path=input_path,
        normalized_records=normalized_records,
        required_fields=["rating_date", "team", "rating_value"],
        duplicate_key_fields=["rating_date", "team", "rating_type"],
        custom_checks=[
            lambda record, row_id: check_record_date(record, row_id, "rating_date")
        ],
    )


def main() -> None:
    args = parse_cli_args("elo_importer")
    run_dir = run(args.input)
    print(run_dir)


if __name__ == "__main__":
    main()

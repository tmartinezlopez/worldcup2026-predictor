"""Importer for controlled team ratings snapshots."""

from __future__ import annotations

from src.ingestion.importers.base import load_records, parse_cli_args, run_basic_import
from src.ingestion.importers.validators import (
    check_at_least_one_field,
    check_record_date,
)


def _to_float_or_none(value):
    if value in (None, ""):
        return None
    return float(value)


def _to_int_or_none(value):
    if value in (None, ""):
        return None
    return int(value)


def normalize_team_rating_record(record: dict) -> dict:
    return {
        "entity_type": "external_team_rating",
        "rating_date": (record.get("rating_date") or record.get("date") or "").strip(),
        "team": (record.get("team") or "").strip(),
        "source": (record.get("source") or "fifa").strip().lower(),
        "rating_type": "team_rating_snapshot",
        "rank_value": _to_int_or_none(record.get("rank")),
        "rating_value": _to_float_or_none(
            record.get("rating_points") or record.get("rating_value")
        ),
    }


def _has_rank_or_rating(record, row_id):
    return check_at_least_one_field(
        record,
        row_id,
        ["rank_value", "rating_value"],
        code="missing_rank_or_rating",
        message="At least one of rank or rating_points must be present",
    )


def import_team_ratings(input_path):
    normalized_records = [
        normalize_team_rating_record(record) for record in load_records(input_path)
    ]
    return run_basic_import(
        source_name="team_ratings_importer",
        source_type="team_ratings",
        input_path=input_path,
        normalized_records=normalized_records,
        required_fields=["rating_date", "team", "source"],
        duplicate_key_fields=["rating_date", "team", "source"],
        custom_checks=[
            lambda record, row_id: check_record_date(record, row_id, "rating_date"),
            _has_rank_or_rating,
        ],
    )


def run(input_path):
    return import_team_ratings(input_path)


def main() -> None:
    args = parse_cli_args("team_ratings_importer")
    run_dir = run(args.input)
    print(run_dir)


if __name__ == "__main__":
    main()

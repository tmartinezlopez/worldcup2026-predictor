"""Importer for player master data."""

from __future__ import annotations

from src.ingestion.importers.base import (
    load_records,
    normalize_bool,
    parse_cli_args,
    run_basic_import,
)
from src.ingestion.importers.validators import check_record_date


def _to_int_or_none(value):
    if value in (None, ""):
        return None
    return int(value)


def normalize_player_record(record: dict) -> dict:
    full_name = (record.get("full_name") or record.get("name") or "").strip()
    display_name = (record.get("display_name") or full_name).strip()
    return {
        "entity_type": "player",
        "full_name": full_name,
        "display_name": display_name,
        "team": (record.get("team") or "").strip() or None,
        "date_of_birth": (record.get("date_of_birth") or "").strip() or None,
        "primary_position": (record.get("primary_position") or "").strip() or None,
        "preferred_foot": (record.get("preferred_foot") or "").strip() or None,
        "height_cm": _to_int_or_none(record.get("height_cm")),
        "club": (record.get("club") or "").strip() or None,
        "is_active": normalize_bool(record.get("is_active", True)),
    }


def run(input_path):
    normalized_records = [
        normalize_player_record(record) for record in load_records(input_path)
    ]
    return run_basic_import(
        source_name="players_importer",
        source_type="players",
        input_path=input_path,
        normalized_records=normalized_records,
        required_fields=["full_name"],
        duplicate_key_fields=["full_name", "team"],
        custom_checks=[
            lambda record, row_id: check_record_date(record, row_id, "date_of_birth")
        ],
    )


def main() -> None:
    args = parse_cli_args("players_importer")
    run_dir = run(args.input)
    print(run_dir)


if __name__ == "__main__":
    main()

"""Importer for team master data."""

from __future__ import annotations

from src.ingestion.importers.base import (
    load_records,
    normalize_bool,
    parse_cli_args,
    run_basic_import,
)


def normalize_team_record(record: dict) -> dict:
    name = (record.get("name") or "").strip()
    official_name = (record.get("official_name") or name).strip()
    short_name = (record.get("short_name") or name).strip()
    country_code = (record.get("country_code") or "").strip().upper() or None
    fifa_code = (record.get("fifa_code") or "").strip().upper() or None
    confederation = (record.get("confederation") or "").strip() or None

    return {
        "entity_type": "team",
        "name": name,
        "official_name": official_name,
        "short_name": short_name,
        "country_code": country_code,
        "fifa_code": fifa_code,
        "confederation": confederation,
        "is_active": normalize_bool(record.get("is_active", True)),
    }


def run(input_path):
    normalized_records = [
        normalize_team_record(record) for record in load_records(input_path)
    ]
    return run_basic_import(
        source_name="teams_importer",
        source_type="teams",
        input_path=input_path,
        normalized_records=normalized_records,
        required_fields=["name"],
        duplicate_key_fields=["name"],
    )


def main() -> None:
    args = parse_cli_args("teams_importer")
    run_dir = run(args.input)
    print(run_dir)


if __name__ == "__main__":
    main()

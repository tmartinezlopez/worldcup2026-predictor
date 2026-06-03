"""Importer for FIFA ranking snapshots."""

from __future__ import annotations

from src.ingestion.importers.base import (
    load_records,
    parse_cli_args,
    run_basic_import,
)
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


def normalize_fifa_ranking_record(record: dict) -> list[dict]:
    rating_date = (record.get("ranking_date") or record.get("date") or "").strip()
    team = (record.get("team") or "").strip()
    fifa_rank = _to_int_or_none(record.get("fifa_rank"))
    fifa_points = _to_float_or_none(record.get("fifa_points"))
    normalized_records: list[dict] = []

    if fifa_rank is not None:
        normalized_records.append(
            {
                "entity_type": "external_team_rating",
                "rating_type": "fifa_rank",
                "rating_date": rating_date,
                "team": team,
                "rank_value": fifa_rank,
                "rating_value": None,
                "source": "fifa",
            }
        )
    if fifa_points is not None:
        normalized_records.append(
            {
                "entity_type": "external_team_rating",
                "rating_type": "fifa_points",
                "rating_date": rating_date,
                "team": team,
                "rank_value": None,
                "rating_value": fifa_points,
                "source": "fifa",
            }
        )
    if not normalized_records:
        normalized_records.append(
            {
                "entity_type": "external_team_rating",
                "rating_type": None,
                "rating_date": rating_date,
                "team": team,
                "rank_value": None,
                "rating_value": None,
                "source": "fifa",
            }
        )
    return normalized_records


def _has_rank_or_points(record, row_id):
    return check_at_least_one_field(
        record,
        row_id,
        ["rank_value", "rating_value"],
        code="missing_rank_or_points",
        message="At least one of fifa_rank or fifa_points must be present",
    )


def run(input_path):
    normalized_records = []
    for record in load_records(input_path):
        normalized_records.extend(normalize_fifa_ranking_record(record))
    return run_basic_import(
        source_name="fifa_ranking_importer",
        source_type="fifa_rankings",
        input_path=input_path,
        normalized_records=normalized_records,
        required_fields=["rating_date", "team"],
        duplicate_key_fields=["rating_date", "team", "rating_type"],
        custom_checks=[
            lambda record, row_id: check_record_date(record, row_id, "rating_date"),
            _has_rank_or_points,
        ],
    )


def main() -> None:
    args = parse_cli_args("fifa_ranking_importer")
    run_dir = run(args.input)
    print(run_dir)


if __name__ == "__main__":
    main()

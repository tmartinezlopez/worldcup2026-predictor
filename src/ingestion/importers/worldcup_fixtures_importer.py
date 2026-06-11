"""Importer for controlled World Cup 2026 real-like fixtures CSVs."""

from __future__ import annotations

from src.identity.normalizers import normalize_team_name
from src.ingestion.importers.base import load_records, parse_cli_args, run_basic_import
from src.ingestion.importers.validators import check_distinct_teams, check_record_date


def _normalized_stage(stage: str, group_value: str | None) -> str | None:
    cleaned = stage.strip()
    if not cleaned:
        return None
    if cleaned.casefold() == "group":
        if group_value:
            return f"Group {group_value.strip().upper()}"
        return "Group Stage"
    return cleaned.title()


def normalize_worldcup_fixture_record(record: dict) -> dict:
    group_value = (record.get("group") or "").strip() or None
    team_a = (record.get("team_a") or "").strip()
    team_b = (record.get("team_b") or "").strip()
    return {
        "entity_type": "worldcup_fixture",
        "match_date": (record.get("match_date") or record.get("date") or "").strip(),
        "stage": _normalized_stage((record.get("stage") or "").strip(), group_value),
        "group": group_value,
        "team_a": team_a,
        "team_b": team_b,
        "team_a_normalized": normalize_team_name(team_a) if team_a else None,
        "team_b_normalized": normalize_team_name(team_b) if team_b else None,
        "venue": (record.get("venue") or "").strip() or None,
        "city": (record.get("city") or "").strip() or None,
        "country": (record.get("country") or "").strip() or None,
        "competition": (
            record.get("competition") or "FIFA World Cup 2026"
        ).strip(),
        "source": (record.get("source") or "local_csv").strip() or "local_csv",
        "status": "scheduled",
    }


def run(input_path):
    normalized_records = [
        normalize_worldcup_fixture_record(record) for record in load_records(input_path)
    ]
    return run_basic_import(
        source_name="worldcup_fixtures_importer",
        source_type="worldcup_fixtures",
        input_path=input_path,
        normalized_records=normalized_records,
        required_fields=["match_date", "team_a", "team_b", "source"],
        duplicate_key_fields=["match_date", "team_a_normalized", "team_b_normalized"],
        custom_checks=[
            check_distinct_teams,
            lambda record, row_id: check_record_date(record, row_id, "match_date"),
        ],
        metadata={
            "sample_notice": (
                "World Cup 2026 fixtures sample is real-like for demo use only "
                "and not an official fixtures dataset."
            )
        },
    )


def main() -> None:
    args = parse_cli_args("worldcup_fixtures_importer")
    run_dir = run(args.input)
    print(run_dir)


if __name__ == "__main__":
    main()

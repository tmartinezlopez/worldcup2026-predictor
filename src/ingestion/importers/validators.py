"""Importer-specific validation helpers."""

from __future__ import annotations

from datetime import datetime

from src.validation.common_checks import check_no_future_date, check_valid_date
from src.validation.results import ValidationIssue


def check_distinct_teams(record: dict, row_id: int | str) -> list[ValidationIssue]:
    team_a = record.get("team_a")
    team_b = record.get("team_b")
    if team_a and team_b and str(team_a).strip() == str(team_b).strip():
        return [
            ValidationIssue(
                row_id=row_id,
                severity="error",
                code="same_team_both_sides",
                message="team_a and team_b must be different",
                field="team_a,team_b",
                value=[team_a, team_b],
            )
        ]
    return []


def check_record_date(
    record: dict, row_id: int | str, field: str = "date"
) -> list[ValidationIssue]:
    return check_valid_date(record, field, row_id)


def check_record_not_future(
    record: dict, row_id: int | str, field: str = "date"
) -> list[ValidationIssue]:
    return check_no_future_date(record, field, row_id, cutoff_date=datetime.now())


def check_at_least_one_field(
    record: dict,
    row_id: int | str,
    fields: list[str],
    code: str,
    message: str,
) -> list[ValidationIssue]:
    if any(record.get(field) not in (None, "") for field in fields):
        return []
    return [
        ValidationIssue(
            row_id=row_id,
            severity="error",
            code=code,
            message=message,
            field=",".join(fields),
            value={field: record.get(field) for field in fields},
        )
    ]

"""Common validation checks for staged records."""

from __future__ import annotations

from datetime import date, datetime

from src.validation.results import ValidationIssue


def check_required_fields(
    record: dict, required_fields: list[str], row_id: str | int
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for field in required_fields:
        if field not in record:
            issues.append(
                ValidationIssue(
                    row_id=row_id,
                    severity="error",
                    code="missing_required_field",
                    message=f"Missing required field: {field}",
                    field=field,
                )
            )
    return issues


def check_non_empty(
    record: dict, fields: list[str], row_id: str | int
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for field in fields:
        if field not in record:
            continue
        value = record[field]
        if value is None or (isinstance(value, str) and not value.strip()):
            issues.append(
                ValidationIssue(
                    row_id=row_id,
                    severity="error",
                    code="empty_value",
                    message=f"Field is empty: {field}",
                    field=field,
                    value=value,
                )
            )
    return issues


def check_non_negative_number(
    record: dict, fields: list[str], row_id: str | int
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for field in fields:
        value = record.get(field)
        if value is None or isinstance(value, bool):
            continue
        if isinstance(value, (int, float)) and value < 0:
            issues.append(
                ValidationIssue(
                    row_id=row_id,
                    severity="error",
                    code="negative_value",
                    message=f"Negative numeric value in field: {field}",
                    field=field,
                    value=value,
                )
            )
    return issues


def check_probability_range(
    record: dict, fields: list[str], row_id: str | int
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for field in fields:
        value = record.get(field)
        if value is None:
            continue
        if isinstance(value, (int, float)) and not 0 <= value <= 1:
            issues.append(
                ValidationIssue(
                    row_id=row_id,
                    severity="error",
                    code="probability_out_of_range",
                    message=f"Probability value out of range in field: {field}",
                    field=field,
                    value=value,
                )
            )
    return issues


def check_valid_date(
    record: dict, field: str, row_id: str | int
) -> list[ValidationIssue]:
    value = record.get(field)
    if value in (None, ""):
        return []

    if isinstance(value, (date, datetime)):
        return []

    if isinstance(value, str):
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            return []
        except ValueError:
            pass

    return [
        ValidationIssue(
            row_id=row_id,
            severity="error",
            code="invalid_date",
            message=f"Invalid date value in field: {field}",
            field=field,
            value=value,
        )
    ]


def check_no_future_date(
    record: dict,
    field: str,
    row_id: str | int,
    cutoff_date: datetime | date | None = None,
) -> list[ValidationIssue]:
    value = record.get(field)
    if value in (None, ""):
        return []

    parsed_value: datetime | date
    if isinstance(value, datetime):
        parsed_value = value
    elif isinstance(value, date):
        parsed_value = value
    elif isinstance(value, str):
        try:
            parsed_value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return []
    else:
        return []

    limit = cutoff_date or datetime.now()
    if isinstance(limit, date) and not isinstance(limit, datetime):
        comparison_value = (
            parsed_value.date() if isinstance(parsed_value, datetime) else parsed_value
        )
        comparison_limit = limit
    else:
        comparison_value = (
            parsed_value
            if isinstance(parsed_value, datetime)
            else datetime.combine(parsed_value, datetime.min.time())
        )
        comparison_limit = limit

    if comparison_value > comparison_limit:
        return [
            ValidationIssue(
                row_id=row_id,
                severity="error",
                code="future_date",
                message=f"Future date detected in field: {field}",
                field=field,
                value=value,
            )
        ]

    return []


def detect_duplicates(
    records: list[dict], key_fields: list[str]
) -> list[ValidationIssue]:
    seen: dict[tuple, str | int] = {}
    issues: list[ValidationIssue] = []

    for index, record in enumerate(records, start=1):
        row_id = record.get("row_id", index)
        key = tuple(record.get(field) for field in key_fields)
        if key in seen:
            issues.append(
                ValidationIssue(
                    row_id=row_id,
                    severity="error",
                    code="duplicate_record",
                    message=(
                        "Duplicate record detected for keys: " + ", ".join(key_fields)
                    ),
                    field=",".join(key_fields),
                    value=list(key),
                )
            )
        else:
            seen[key] = row_id

    return issues

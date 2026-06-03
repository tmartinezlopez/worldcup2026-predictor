"""Generic dataset validation for staged records."""

from __future__ import annotations

from collections import defaultdict

from src.validation.common_checks import (
    check_non_empty,
    check_non_negative_number,
    check_probability_range,
    check_required_fields,
    detect_duplicates,
)
from src.validation.results import ValidationIssue, ValidationResult


class DatasetValidator:
    def __init__(
        self,
        required_fields: list[str],
        duplicate_key_fields: list[str] | None = None,
    ) -> None:
        self.required_fields = required_fields
        self.duplicate_key_fields = duplicate_key_fields or []

    def validate(
        self, records: list[dict]
    ) -> tuple[list[dict], list[dict], ValidationResult]:
        issues_by_row: dict[str | int, list[ValidationIssue]] = defaultdict(list)
        duplicate_issues = (
            detect_duplicates(records, self.duplicate_key_fields)
            if self.duplicate_key_fields
            else []
        )

        for issue in duplicate_issues:
            issues_by_row[issue.row_id].append(issue)

        valid_records: list[dict] = []
        rejected_records: list[dict] = []

        for index, record in enumerate(records, start=1):
            row_id = record.get("row_id", index)
            row_issues: list[ValidationIssue] = []
            row_issues.extend(
                check_required_fields(record, self.required_fields, row_id)
            )
            row_issues.extend(check_non_empty(record, self.required_fields, row_id))

            numeric_fields = [
                field
                for field, value in record.items()
                if field != "row_id" and isinstance(value, (int, float))
            ]
            probability_fields = [
                field
                for field in numeric_fields
                if "prob" in field or "probability" in field
            ]

            row_issues.extend(check_non_negative_number(record, numeric_fields, row_id))
            row_issues.extend(
                check_probability_range(record, probability_fields, row_id)
            )
            row_issues.extend(issues_by_row.get(row_id, []))

            if row_issues:
                rejected_records.append(
                    {
                        "record": record,
                        "validation_errors": [issue.to_dict() for issue in row_issues],
                    }
                )
                issues_by_row[row_id].extend(row_issues)
            else:
                valid_records.append(record)

        all_issues: list[ValidationIssue] = []
        seen_issue_keys: set[tuple] = set()
        for row_issues in issues_by_row.values():
            for issue in row_issues:
                issue_key = (
                    issue.row_id,
                    issue.code,
                    issue.field,
                    str(issue.value),
                )
                if issue_key in seen_issue_keys:
                    continue
                seen_issue_keys.add(issue_key)
                all_issues.append(issue)

        rows_read = len(records)
        rows_rejected = len(rejected_records)
        rows_valid = len(valid_records)
        rejection_rate = rows_rejected / rows_read if rows_read else 0.0

        if rejection_rate == 0 and not all_issues:
            status = "passed"
        elif rejection_rate < 0.05:
            status = "passed_with_warnings"
        elif rejection_rate < 0.40:
            status = "needs_review"
        else:
            status = "blocked"

        result = ValidationResult(
            rows_read=rows_read,
            rows_valid=rows_valid,
            rows_rejected=rows_rejected,
            issues=all_issues,
            unresolved_entities=[],
            duplicate_count=len(duplicate_issues),
            status=status,
        )
        return valid_records, rejected_records, result

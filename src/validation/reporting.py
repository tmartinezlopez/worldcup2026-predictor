"""Validation report builders and writers."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from src.validation.results import ValidationResult


def build_validation_report(result: ValidationResult) -> dict:
    issue_counts = Counter(issue.code for issue in result.issues)
    value_counts: dict[str, Counter] = defaultdict(Counter)

    for issue in result.issues:
        if issue.value is None:
            continue
        key = f"{issue.code}:{issue.field or 'unknown'}"
        value_counts[key][str(issue.value)] += 1

    top_issue_values = {
        key: [
            {"value": value, "count": count} for value, count in counter.most_common(5)
        ]
        for key, counter in value_counts.items()
    }

    rejection_rate = (
        result.rows_rejected / result.rows_read if result.rows_read else 0.0
    )

    return {
        "rows_read": result.rows_read,
        "rows_valid": result.rows_valid,
        "rows_rejected": result.rows_rejected,
        "rejection_rate": rejection_rate,
        "duplicate_count": result.duplicate_count,
        "unresolved_entities": result.unresolved_entities,
        "issue_counts_by_code": dict(issue_counts),
        "top_issue_values": top_issue_values,
        "status": result.status,
    }


def write_validation_report(run_dir: Path, report: dict) -> Path:
    path = run_dir / "validation_report.json"
    path.write_text(
        json.dumps(report, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    return path


def _recommendation_for_status(status: str) -> str:
    mapping = {
        "passed": "accept",
        "passed_with_warnings": "accept_with_warnings",
        "needs_review": "needs_human_review",
        "blocked": "blocked",
    }
    return mapping.get(status, "needs_human_review")


def write_review_report(run_dir: Path, report: dict) -> Path:
    path = run_dir / "review_report.md"

    lines = [
        "# Review Report",
        "",
        "## Summary",
        f"- Status: `{report['status']}`",
        f"- Recommendation: `{_recommendation_for_status(report['status'])}`",
        f"- Rows read: {report['rows_read']}",
        f"- Rows valid: {report['rows_valid']}",
        f"- Rows rejected: {report['rows_rejected']}",
        f"- Rejection rate: {report['rejection_rate']:.2%}",
        f"- Duplicate count: {report['duplicate_count']}",
        "",
        "## Top Issues",
    ]

    if report["issue_counts_by_code"]:
        for code, count in sorted(
            report["issue_counts_by_code"].items(),
            key=lambda item: (-item[1], item[0]),
        ):
            lines.append(f"- `{code}`: {count}")
    else:
        lines.append("- No issues detected.")

    lines.extend(["", "## Frequent Problematic Values"])
    if report["top_issue_values"]:
        for key, values in sorted(report["top_issue_values"].items()):
            lines.append(f"- `{key}`: {values}")
    else:
        lines.append("- No problematic values recorded.")

    lines.extend(["", "## Unresolved Entities"])
    if report["unresolved_entities"]:
        for entity in report["unresolved_entities"]:
            lines.append(f"- {entity}")
    else:
        lines.append("- None.")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path

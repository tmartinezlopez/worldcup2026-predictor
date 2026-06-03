"""Source audit helpers for candidate real-world datasets."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class SourceAuditConfig:
    source_name: str
    source_type: str
    expected_format: str
    url: str | None = None
    license: str | None = None
    local_sample_path: str | None = None
    importer_name: str | None = None
    notes: str | None = None


@dataclass
class SourceAuditResult:
    source_name: str
    status: str
    decision: str
    rows_read: int
    rows_valid: int
    rows_rejected: int
    rejection_rate: float
    duplicate_count: int
    unresolved_entities_count: int
    issue_counts_by_code: dict[str, int]
    strengths: list[str]
    risks: list[str]
    recommendation: str
    report_path: str | None = None


def decide_source_status(validation_report: dict) -> tuple[str, str]:
    rejection_rate = validation_report.get("rejection_rate", 0.0)
    duplicate_count = validation_report.get("duplicate_count", 0)
    issue_counts = validation_report.get("issue_counts_by_code", {})
    unresolved_entities = validation_report.get("unresolved_entities", [])

    missing_required = issue_counts.get("missing_required_field", 0)

    if missing_required > 0 and rejection_rate >= 0.20:
        return "blocked", "rejected"
    if rejection_rate < 0.05 and duplicate_count <= 2:
        return "passed", "accepted"
    if rejection_rate < 0.20:
        return "passed_with_warnings", "accepted_with_warnings"
    if rejection_rate < 0.40 or missing_required > 0 or unresolved_entities:
        return "needs_review", "manual_review"
    return "blocked", "rejected"


def build_source_audit_report(
    config: SourceAuditConfig,
    validation_report: dict,
    extra_notes: list[str] | None = None,
) -> dict:
    status, decision = decide_source_status(validation_report)

    strengths: list[str] = []
    risks: list[str] = []

    if validation_report.get("rows_valid", 0) > 0:
        strengths.append("The sample produced valid normalized rows.")
    if validation_report.get("duplicate_count", 0) == 0:
        strengths.append("No duplicate rows were detected in the audited sample.")
    if validation_report.get("rejection_rate", 1.0) < 0.20:
        strengths.append("Rejection rate is within a potentially usable range.")

    if not config.license or "unknown" in config.license.lower():
        risks.append("License status is not fully verified yet.")
    if validation_report.get("rows_rejected", 0) > 0:
        risks.append("The sample contains rejected rows that require review.")
    if validation_report.get("unresolved_entities"):
        risks.append("There are unresolved entities that may block safe onboarding.")

    if extra_notes:
        risks.extend(extra_notes)

    recommendation_map = {
        "accepted": (
            "Proceed with a deeper manual source review before enabling real ingestion."
        ),
        "accepted_with_warnings": (
            "Proceed carefully and document follow-up cleanup tasks."
        ),
        "manual_review": (
            "Manual source review is required before accepting this source."
        ),
        "rejected": "Do not enable this source until core issues are resolved.",
    }

    result = SourceAuditResult(
        source_name=config.source_name,
        status=status,
        decision=decision,
        rows_read=validation_report.get("rows_read", 0),
        rows_valid=validation_report.get("rows_valid", 0),
        rows_rejected=validation_report.get("rows_rejected", 0),
        rejection_rate=validation_report.get("rejection_rate", 0.0),
        duplicate_count=validation_report.get("duplicate_count", 0),
        unresolved_entities_count=len(validation_report.get("unresolved_entities", [])),
        issue_counts_by_code=validation_report.get("issue_counts_by_code", {}),
        strengths=strengths,
        risks=risks,
        recommendation=recommendation_map[decision],
    )

    report = asdict(result)
    report["config"] = asdict(config)
    report["validation_report"] = validation_report
    return report


def write_source_audit_report(run_dir: Path, audit_report: dict) -> Path:
    path = run_dir / "source_audit_report.json"
    report = dict(audit_report)
    report["report_path"] = str(path)
    path.write_text(
        json.dumps(report, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    return path


def write_source_audit_markdown(run_dir: Path, audit_report: dict) -> Path:
    path = run_dir / "source_audit_report.md"
    lines = [
        "# Source Audit Report",
        "",
        f"- Source: `{audit_report['source_name']}`",
        f"- Status: `{audit_report['status']}`",
        f"- Decision: `{audit_report['decision']}`",
        f"- Rows read: {audit_report['rows_read']}",
        f"- Rows valid: {audit_report['rows_valid']}",
        f"- Rows rejected: {audit_report['rows_rejected']}",
        f"- Rejection rate: {audit_report['rejection_rate']:.2%}",
        f"- Duplicate count: {audit_report['duplicate_count']}",
        f"- Unresolved entities: {audit_report['unresolved_entities_count']}",
        "",
        "## Strengths",
    ]
    if audit_report["strengths"]:
        lines.extend(f"- {item}" for item in audit_report["strengths"])
    else:
        lines.append("- None recorded.")

    lines.extend(["", "## Risks"])
    if audit_report["risks"]:
        lines.extend(f"- {item}" for item in audit_report["risks"])
    else:
        lines.append("- None recorded.")

    lines.extend(["", "## Recommendation", audit_report["recommendation"], ""])
    path.write_text("\n".join(lines), encoding="utf-8")
    return path

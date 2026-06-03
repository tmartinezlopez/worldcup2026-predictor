import json

from src.ingestion.source_audit import (
    SourceAuditConfig,
    build_source_audit_report,
    decide_source_status,
    write_source_audit_markdown,
    write_source_audit_report,
)


def test_decide_source_status_accepted():
    report = {
        "rejection_rate": 0.01,
        "duplicate_count": 0,
        "issue_counts_by_code": {},
        "unresolved_entities": [],
    }
    assert decide_source_status(report) == (
        "passed",
        "accepted",
    )


def test_decide_source_status_accepted_with_warnings():
    report = {
        "rejection_rate": 0.10,
        "duplicate_count": 1,
        "issue_counts_by_code": {},
        "unresolved_entities": [],
    }
    assert decide_source_status(report) == (
        "passed_with_warnings",
        "accepted_with_warnings",
    )


def test_decide_source_status_manual_review():
    report = {
        "rejection_rate": 0.30,
        "duplicate_count": 1,
        "issue_counts_by_code": {},
        "unresolved_entities": [],
    }
    assert decide_source_status(report) == (
        "needs_review",
        "manual_review",
    )


def test_decide_source_status_rejected():
    report = {
        "rejection_rate": 0.50,
        "duplicate_count": 1,
        "issue_counts_by_code": {},
        "unresolved_entities": [],
    }
    assert decide_source_status(report) == (
        "blocked",
        "rejected",
    )


def test_build_source_audit_report_includes_key_fields():
    config = SourceAuditConfig(
        source_name="sample_source",
        source_type="historical_results",
        expected_format="csv",
    )
    report = build_source_audit_report(
        config,
        {
            "rows_read": 10,
            "rows_valid": 9,
            "rows_rejected": 1,
            "rejection_rate": 0.1,
            "duplicate_count": 0,
            "unresolved_entities": [],
            "issue_counts_by_code": {"invalid_date": 1},
        },
    )

    assert report["source_name"] == "sample_source"
    assert report["issue_counts_by_code"]["invalid_date"] == 1
    assert "config" in report


def test_write_source_audit_report_creates_json(tmp_path):
    report = {"source_name": "sample", "status": "passed", "decision": "accepted"}

    path = write_source_audit_report(tmp_path, report)

    assert path.is_file()
    assert json.loads(path.read_text(encoding="utf-8"))["source_name"] == "sample"


def test_write_source_audit_markdown_creates_md(tmp_path):
    report = {
        "source_name": "sample",
        "status": "passed",
        "decision": "accepted",
        "rows_read": 1,
        "rows_valid": 1,
        "rows_rejected": 0,
        "rejection_rate": 0.0,
        "duplicate_count": 0,
        "unresolved_entities_count": 0,
        "strengths": ["Good sample"],
        "risks": ["Unknown license"],
        "recommendation": "Proceed carefully",
    }

    path = write_source_audit_markdown(tmp_path, report)

    assert path.is_file()
    assert "Source Audit Report" in path.read_text(encoding="utf-8")

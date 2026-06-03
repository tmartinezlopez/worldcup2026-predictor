"""Utilities for creating safe staging import runs."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path

from src.staging.jsonl import write_jsonl
from src.staging.metadata import load_metadata, write_metadata
from src.staging.paths import make_import_run_dir
from src.validation.reporting import (
    build_validation_report,
    write_review_report,
    write_validation_report,
)
from src.validation.results import ValidationResult


def create_import_run(
    source_name: str,
    source_type: str,
    original_path: str | Path | None = None,
    metadata: dict | None = None,
) -> Path:
    run_dir = make_import_run_dir(source_name)
    original_filename = None
    original_format = None
    if original_path is not None:
        original_path = Path(original_path)
        original_filename = original_path.name
        original_format = original_path.suffix.lstrip(".") or None

    write_metadata(
        run_dir,
        {
            "source_name": source_name,
            "source_type": source_type,
            "created_at": datetime.now(UTC),
            "original_filename": original_filename,
            "original_format": original_format,
            "row_count": None,
            "notes": None,
            **(metadata or {}),
        },
    )
    return run_dir


def copy_original_to_run_dir(run_dir: Path, original_path: str | Path) -> Path:
    original_path = Path(original_path)
    destination = run_dir / f"original{original_path.suffix}"
    shutil.copy2(original_path, destination)
    return destination


def finalize_import_run(
    run_dir: Path,
    normalized_records: list[dict],
    valid_records: list[dict],
    rejected_records: list[dict],
    validation_result: ValidationResult,
) -> dict:
    write_jsonl(run_dir / "normalized.jsonl", normalized_records)
    write_jsonl(run_dir / "valid.jsonl", valid_records)
    write_jsonl(run_dir / "rejected.jsonl", rejected_records)

    report = build_validation_report(validation_result)
    write_validation_report(run_dir, report)
    write_review_report(run_dir, report)

    metadata = load_metadata(run_dir)
    metadata["row_count"] = validation_result.rows_read
    write_metadata(run_dir, metadata)
    return report

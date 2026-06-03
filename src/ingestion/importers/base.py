"""Shared helpers for controlled local importers."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from src.ingestion.import_run import (
    copy_original_to_run_dir,
    create_import_run,
    finalize_import_run,
)
from src.validation.dataset_validator import DatasetValidator


def load_records_from_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as file_handle:
        return list(csv.DictReader(file_handle))


def load_records_from_json(path: Path) -> list[dict]:
    content = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(content, list):
        raise ValueError("JSON input must be a list of objects")
    return content


def load_records_from_jsonl(path: Path) -> list[dict]:
    records: list[dict] = []
    with path.open("r", encoding="utf-8") as file_handle:
        for line in file_handle:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def load_records(path: Path) -> list[dict]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return load_records_from_csv(path)
    if suffix == ".json":
        return load_records_from_json(path)
    if suffix == ".jsonl":
        return load_records_from_jsonl(path)
    raise ValueError(f"Unsupported input extension: {path.suffix}")


def normalize_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    normalized = str(value).strip().lower()
    return normalized in {"1", "true", "yes", "y", "si", "sí"}


def parse_cli_args(importer_name: str) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=f"Run {importer_name}")
    parser.add_argument("--input", required=True, type=Path, help="Input file path")
    return parser.parse_args()


def run_basic_import(
    source_name: str,
    source_type: str,
    input_path: Path,
    normalized_records: list[dict],
    required_fields: list[str],
    duplicate_key_fields: list[str] | None = None,
    metadata: dict | None = None,
    custom_checks=None,
) -> Path:
    run_dir = create_import_run(
        source_name=source_name,
        source_type=source_type,
        original_path=input_path,
        metadata=metadata,
    )
    copy_original_to_run_dir(run_dir, input_path)

    validator = DatasetValidator(
        required_fields=required_fields,
        duplicate_key_fields=duplicate_key_fields,
        custom_checks=custom_checks or [],
    )
    valid_records, rejected_records, validation_result = validator.validate(
        normalized_records
    )
    finalize_import_run(
        run_dir=run_dir,
        normalized_records=normalized_records,
        valid_records=valid_records,
        rejected_records=rejected_records,
        validation_result=validation_result,
    )
    return run_dir

"""Metadata helpers for staging import runs."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any


def _serialize_metadata_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: _serialize_metadata_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_serialize_metadata_value(item) for item in value]
    return value


def write_metadata(run_dir: Path, metadata: dict) -> Path:
    """Write import-run metadata to metadata.json."""
    path = run_dir / "metadata.json"
    serialized = _serialize_metadata_value(metadata)
    path.write_text(
        json.dumps(serialized, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    return path


def load_metadata(run_dir: Path) -> dict:
    """Load metadata.json from an import run directory."""
    path = run_dir / "metadata.json"
    return json.loads(path.read_text(encoding="utf-8"))

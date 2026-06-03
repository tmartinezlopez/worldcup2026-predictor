"""Path helpers for staging import runs."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STAGING_ROOT = PROJECT_ROOT / "data" / "staging" / "imports"


def get_staging_root() -> Path:
    """Return the staging imports root."""
    return STAGING_ROOT


def ensure_staging_dirs() -> Path:
    """Ensure the staging imports root exists."""
    root = get_staging_root()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _slugify_source_name(source_name: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", source_name.strip().lower())
    return normalized.strip("_") or "unknown_source"


def make_import_run_dir(source_name: str, timestamp: datetime | None = None) -> Path:
    """Create and return a timestamped staging directory for one import run."""
    run_timestamp = timestamp or datetime.now(UTC)
    source_dir = ensure_staging_dirs() / _slugify_source_name(source_name)
    source_dir.mkdir(parents=True, exist_ok=True)

    run_dir = source_dir / run_timestamp.strftime("%Y%m%dT%H%M%SZ")
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir

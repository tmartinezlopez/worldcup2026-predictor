"""JSONL read/write helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable


def write_jsonl(path: Path, records: Iterable[dict]) -> None:
    """Write records to JSONL, replacing any previous content."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file_handle:
        for record in records:
            file_handle.write(json.dumps(record, ensure_ascii=True, default=str))
            file_handle.write("\n")


def read_jsonl(path: Path) -> list[dict]:
    """Read a JSONL file into memory."""
    records: list[dict] = []
    with path.open("r", encoding="utf-8") as file_handle:
        for line in file_handle:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def append_jsonl(path: Path, record: dict) -> None:
    """Append one record to an existing or new JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file_handle:
        file_handle.write(json.dumps(record, ensure_ascii=True, default=str))
        file_handle.write("\n")

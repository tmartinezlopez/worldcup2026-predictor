"""Local registry for audited candidate sources."""

from __future__ import annotations

import json
from pathlib import Path


def load_source_registry(path: str = "data/staging/source_registry.json") -> list[dict]:
    registry_path = Path(path)
    if not registry_path.exists():
        return []
    return json.loads(registry_path.read_text(encoding="utf-8"))


def save_source_registry(
    entries: list[dict], path: str = "data/staging/source_registry.json"
) -> None:
    registry_path = Path(path)
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        json.dumps(entries, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )


def upsert_source_entry(
    entry: dict, path: str = "data/staging/source_registry.json"
) -> None:
    entries = load_source_registry(path)
    updated = False
    for index, existing in enumerate(entries):
        if existing.get("source_name") == entry.get("source_name"):
            entries[index] = entry
            updated = True
            break
    if not updated:
        entries.append(entry)
    save_source_registry(entries, path)

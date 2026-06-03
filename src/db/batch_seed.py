"""Seed controlled batch definitions from configuration."""

from __future__ import annotations

from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.connection import get_session
from src.db.models import Batch

CONFIG_PATH = Path("config/batches.yaml")


def load_batch_definitions(config_path: Path | None = None) -> list[dict]:
    path = config_path or CONFIG_PATH
    content = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    batches_config = content.get("batches") or {}
    definitions = batches_config.get("definitions") or []
    if not isinstance(definitions, list):
        raise ValueError(
            "config/batches.yaml must define a list under batches.definitions"
        )
    return definitions


def seed_batches(session: Session, config_path: Path | None = None) -> dict[str, int]:
    created = 0
    skipped = 0

    for definition in load_batch_definitions(config_path):
        existing = session.scalar(
            select(Batch).where(Batch.code == definition["code"]).order_by(Batch.id)
        )
        if existing is not None:
            skipped += 1
            continue

        batch = Batch(
            code=definition["code"],
            name=definition["name"],
            stage=definition["stage"],
            sequence_order=int(definition["sequence_order"]),
            first_match_start=None,
            cutoff_time=None,
            status=definition.get("status", "scheduled"),
        )
        session.add(batch)
        session.flush()
        created += 1

    return {"created": created, "skipped": skipped}


def main() -> None:
    with get_session() as session:
        result = seed_batches(session)
        session.commit()
    print(f"created={result['created']}")
    print(f"skipped={result['skipped']}")


if __name__ == "__main__":
    main()

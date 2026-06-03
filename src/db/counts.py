"""Lightweight table counts for development verification."""

from __future__ import annotations

from sqlalchemy import func, inspect, select
from sqlalchemy.orm import Session

from src.db.connection import get_session
from src.db.models import (
    Batch,
    Competition,
    DataSource,
    Match,
    Prediction,
    Team,
    TeamAlias,
)


def get_table_counts(session: Session) -> dict[str, int]:
    inspector = inspect(session.bind)
    existing_tables = set(inspector.get_table_names())

    table_models = {
        "teams": Team,
        "team_aliases": TeamAlias,
        "competitions": Competition,
        "matches": Match,
        "data_sources": DataSource,
        "batches": Batch,
        "predictions": Prediction,
    }

    counts: dict[str, int] = {}
    for table_name, model in table_models.items():
        if table_name not in existing_tables:
            continue
        counts[table_name] = int(
            session.scalar(select(func.count()).select_from(model)) or 0
        )
    return counts


def main() -> None:
    with get_session() as session:
        counts = get_table_counts(session)

    for table_name in (
        "teams",
        "team_aliases",
        "competitions",
        "matches",
        "data_sources",
        "batches",
        "predictions",
    ):
        if table_name in counts:
            print(f"{table_name}: {counts[table_name]}")


if __name__ == "__main__":
    main()

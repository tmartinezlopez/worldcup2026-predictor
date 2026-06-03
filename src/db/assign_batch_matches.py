"""Assign scheduled matches to configured batches."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.batch_seed import load_batch_definitions
from src.db.connection import get_session
from src.db.models import Batch, BatchMatch, Match


def _normalize_text(value: object) -> str | None:
    if value in (None, ""):
        return None
    return str(value).strip().casefold()


def _match_definition(definition: dict, match: Match) -> bool:
    definition_stage = _normalize_text(definition.get("stage"))
    match_stage = _normalize_text(match.stage)
    if definition_stage != match_stage:
        return False

    definition_matchday = definition.get("matchday")
    if definition_matchday is None:
        return True

    if match.matchday is None:
        return False

    return int(definition_matchday) == int(match.matchday)


def assign_batch_matches(session: Session) -> dict[str, int]:
    definitions = load_batch_definitions()
    batches_by_code = {
        batch.code: batch
        for batch in session.scalars(select(Batch).order_by(Batch.sequence_order)).all()
    }
    existing_pairs = {
        (batch_match.batch_id, batch_match.match_id)
        for batch_match in session.scalars(select(BatchMatch)).all()
    }

    assigned = 0
    skipped = 0

    matches = session.scalars(
        select(Match).where(Match.status == "scheduled").order_by(Match.date, Match.id)
    ).all()
    for match in matches:
        matched_definition = next(
            (
                definition
                for definition in definitions
                if _match_definition(definition, match)
            ),
            None,
        )
        if matched_definition is None:
            skipped += 1
            continue

        batch = batches_by_code.get(matched_definition["code"])
        if batch is None:
            skipped += 1
            continue

        pair = (batch.id, match.id)
        if pair in existing_pairs:
            skipped += 1
            continue

        order_in_batch = int(match.matchday or 0) or None
        session.add(
            BatchMatch(
                batch_id=batch.id,
                match_id=match.id,
                order_in_batch=order_in_batch,
            )
        )
        session.flush()
        existing_pairs.add(pair)
        assigned += 1

    return {"assigned": assigned, "skipped": skipped}


def main() -> None:
    with get_session() as session:
        result = assign_batch_matches(session)
        session.commit()
    print(f"assigned={result['assigned']}")
    print(f"skipped={result['skipped']}")


if __name__ == "__main__":
    main()

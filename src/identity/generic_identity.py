"""Generic alias helpers for lower-priority identity entities."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.identity.matching import MatchCandidate, suggest_matches
from src.identity.normalizers import normalize_text
from src.identity.team_identity import IdentityResolutionResult


def resolve_alias(
    session: Session,
    alias_model: type,
    raw_name: str,
    entity_fk_name: str,
    source_id: int | None = None,
    normalizer=normalize_text,
) -> IdentityResolutionResult:
    normalized_value = normalizer(raw_name)
    aliases = list(
        session.scalars(
            select(alias_model)
            .where(
                alias_model.is_approved.is_(True),
                alias_model.normalized_alias == normalized_value,
            )
            .order_by(alias_model.id)
        )
    )

    if source_id is not None:
        aliases = [
            alias
            for alias in aliases
            if getattr(alias, "source_id", None) in (None, source_id)
        ]

    if aliases:
        alias = aliases[0]
        return IdentityResolutionResult(
            resolved=True,
            entity_id=getattr(alias, entity_fk_name),
            raw_value=raw_name,
            normalized_value=normalized_value,
            resolution_type="exact_alias",
            confidence=alias.confidence,
            suggestions=[],
        )

    return IdentityResolutionResult(
        resolved=False,
        entity_id=None,
        raw_value=raw_name,
        normalized_value=normalized_value,
        resolution_type="unresolved",
        confidence=None,
        suggestions=suggest_aliases(
            session,
            alias_model,
            raw_name,
            normalizer=normalizer,
        ),
    )


def add_alias(
    session: Session,
    alias_model: type,
    entity_fk_name: str,
    entity_id: int,
    alias: str,
    source_id: int | None = None,
    confidence: float = 1.0,
    is_approved: bool = False,
    normalizer=normalize_text,
):
    record = alias_model(
        **{
            entity_fk_name: entity_id,
            "source_id": source_id,
            "alias": alias,
            "normalized_alias": normalizer(alias),
            "confidence": confidence,
            "is_approved": is_approved,
        }
    )
    session.add(record)
    session.flush()
    return record


def suggest_aliases(
    session: Session,
    alias_model: type,
    raw_name: str,
    limit: int = 5,
    normalizer=normalize_text,
) -> list[MatchCandidate]:
    aliases = session.scalars(
        select(alias_model)
        .where(alias_model.is_approved.is_(True))
        .order_by(alias_model.id)
    )
    candidates = [
        MatchCandidate(
            entity_id=getattr(alias, column_name),
            label=alias.alias,
            match_type="approved_alias",
            metadata={"normalized_value": alias.normalized_alias},
        )
        for alias in aliases
        for column_name in alias.__table__.columns.keys()
        if column_name.endswith("_id") and column_name != "source_id"
    ]
    return suggest_matches(raw_name, candidates, limit=limit)

"""Team identity resolution based on approved aliases."""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import Team, TeamAlias
from src.identity.matching import MatchCandidate, suggest_matches
from src.identity.normalizers import normalize_team_name


@dataclass
class IdentityResolutionResult:
    resolved: bool
    entity_id: int | None
    raw_value: str
    normalized_value: str
    resolution_type: str
    confidence: float | None
    suggestions: list[MatchCandidate] = field(default_factory=list)


def add_team_alias(
    session: Session,
    team_id: int,
    alias: str,
    source_id: int | None = None,
    confidence: float = 1.0,
    is_approved: bool = False,
) -> TeamAlias:
    team_alias = TeamAlias(
        team_id=team_id,
        source_id=source_id,
        alias=alias,
        normalized_alias=normalize_team_name(alias),
        confidence=confidence,
        is_approved=is_approved,
    )
    session.add(team_alias)
    session.flush()
    return team_alias


def get_team_aliases(session: Session) -> list[TeamAlias]:
    return list(session.scalars(select(TeamAlias).order_by(TeamAlias.id)))


def _team_suggestion_candidates(session: Session) -> list[MatchCandidate]:
    alias_rows = session.execute(
        select(TeamAlias, Team)
        .join(Team, Team.id == TeamAlias.team_id)
        .where(TeamAlias.is_approved.is_(True))
    ).all()

    candidates: list[MatchCandidate] = []
    seen: set[tuple[int, str]] = set()

    for alias, team in alias_rows:
        key = (team.id, alias.normalized_alias)
        if key in seen:
            continue
        seen.add(key)
        candidates.append(
            MatchCandidate(
                entity_id=team.id,
                label=alias.alias,
                match_type="approved_alias",
                metadata={"normalized_value": alias.normalized_alias},
            )
        )

    for team in session.scalars(select(Team).order_by(Team.id)):
        for label in (team.name, team.official_name, team.short_name):
            normalized = normalize_team_name(label)
            key = (team.id, normalized)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(
                MatchCandidate(
                    entity_id=team.id,
                    label=label,
                    match_type="canonical_name",
                    metadata={"normalized_value": normalized},
                )
            )

    return candidates


def suggest_team_aliases(
    session: Session, raw_name: str, limit: int = 5
) -> list[MatchCandidate]:
    return suggest_matches(raw_name, _team_suggestion_candidates(session), limit=limit)


def resolve_team_id(
    session: Session, raw_name: str, source_id: int | None = None
) -> IdentityResolutionResult:
    normalized_value = normalize_team_name(raw_name)

    statement = (
        select(TeamAlias)
        .where(
            TeamAlias.is_approved.is_(True),
            TeamAlias.normalized_alias == normalized_value,
        )
        .order_by(TeamAlias.id)
    )
    alias_rows = list(session.scalars(statement))

    if source_id is not None:
        source_specific = [
            alias for alias in alias_rows if alias.source_id in (None, source_id)
        ]
        exact_aliases = sorted(
            source_specific,
            key=lambda alias: (
                0 if alias.source_id == source_id else 1,
                alias.id,
            ),
        )
    else:
        exact_aliases = alias_rows

    if exact_aliases:
        matched_alias = exact_aliases[0]
        return IdentityResolutionResult(
            resolved=True,
            entity_id=matched_alias.team_id,
            raw_value=raw_name,
            normalized_value=normalized_value,
            resolution_type="exact_alias",
            confidence=matched_alias.confidence,
            suggestions=[],
        )

    return IdentityResolutionResult(
        resolved=False,
        entity_id=None,
        raw_value=raw_name,
        normalized_value=normalized_value,
        resolution_type="unresolved",
        confidence=None,
        suggestions=suggest_team_aliases(session, raw_name, limit=5),
    )


def require_team_id(
    session: Session, raw_name: str, source_id: int | None = None
) -> int:
    resolution = resolve_team_id(session, raw_name, source_id=source_id)
    if not resolution.resolved or resolution.entity_id is None:
        raise ValueError(f"Could not resolve team alias: {raw_name}")
    return resolution.entity_id

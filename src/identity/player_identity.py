"""Player identity resolution with optional team and club context."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import Player, PlayerAlias
from src.identity.matching import MatchCandidate, suggest_matches
from src.identity.normalizers import normalize_player_name
from src.identity.team_identity import IdentityResolutionResult


def add_player_alias(
    session: Session,
    player_id: int,
    alias: str,
    source_id: int | None = None,
    team_id_context: int | None = None,
    club_id_context: int | None = None,
    confidence: float = 1.0,
    is_approved: bool = False,
) -> PlayerAlias:
    player_alias = PlayerAlias(
        player_id=player_id,
        source_id=source_id,
        alias=alias,
        normalized_alias=normalize_player_name(alias),
        team_id_context=team_id_context,
        club_id_context=club_id_context,
        confidence=confidence,
        is_approved=is_approved,
    )
    session.add(player_alias)
    session.flush()
    return player_alias


def _player_context_rank(
    alias: PlayerAlias,
    team_id_context: int | None,
    club_id_context: int | None,
    source_id: int | None,
) -> tuple[int, int, int, int]:
    return (
        0 if source_id is not None and alias.source_id == source_id else 1,
        (
            0
            if team_id_context is not None and alias.team_id_context == team_id_context
            else 1
        ),
        (
            0
            if club_id_context is not None and alias.club_id_context == club_id_context
            else 1
        ),
        alias.id,
    )


def _player_suggestion_candidates(session: Session) -> list[MatchCandidate]:
    alias_rows = session.scalars(
        select(PlayerAlias)
        .where(PlayerAlias.is_approved.is_(True))
        .order_by(PlayerAlias.id)
    )
    candidates: list[MatchCandidate] = []
    seen: set[tuple[int, str, int | None, int | None]] = set()

    for alias in alias_rows:
        key = (
            alias.player_id,
            alias.normalized_alias,
            alias.team_id_context,
            alias.club_id_context,
        )
        if key in seen:
            continue
        seen.add(key)
        candidates.append(
            MatchCandidate(
                entity_id=alias.player_id,
                label=alias.alias,
                match_type="approved_alias",
                metadata={
                    "normalized_value": alias.normalized_alias,
                    "team_id_context": alias.team_id_context,
                    "club_id_context": alias.club_id_context,
                },
            )
        )

    for player in session.scalars(select(Player).order_by(Player.id)):
        for label in (player.display_name, player.full_name):
            normalized = normalize_player_name(label)
            key = (player.id, normalized, None, None)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(
                MatchCandidate(
                    entity_id=player.id,
                    label=label,
                    match_type="canonical_name",
                    metadata={"normalized_value": normalized},
                )
            )

    return candidates


def suggest_player_aliases(
    session: Session,
    raw_name: str,
    team_id_context: int | None = None,
    club_id_context: int | None = None,
    limit: int = 5,
) -> list[MatchCandidate]:
    candidates = _player_suggestion_candidates(session)
    suggestions = suggest_matches(raw_name, candidates, limit=limit)
    suggestions.sort(
        key=lambda candidate: (
            (
                0
                if team_id_context is not None
                and candidate.metadata.get("team_id_context") == team_id_context
                else 1
            ),
            (
                0
                if club_id_context is not None
                and candidate.metadata.get("club_id_context") == club_id_context
                else 1
            ),
            -candidate.score,
            candidate.label,
        )
    )
    return suggestions[:limit]


def resolve_player_id(
    session: Session,
    raw_name: str,
    team_id_context: int | None = None,
    club_id_context: int | None = None,
    source_id: int | None = None,
) -> IdentityResolutionResult:
    normalized_value = normalize_player_name(raw_name)
    exact_aliases = list(
        session.scalars(
            select(PlayerAlias)
            .where(
                PlayerAlias.is_approved.is_(True),
                PlayerAlias.normalized_alias == normalized_value,
            )
            .order_by(PlayerAlias.id)
        )
    )

    if exact_aliases:
        ranked_aliases = sorted(
            exact_aliases,
            key=lambda alias: _player_context_rank(
                alias, team_id_context, club_id_context, source_id
            ),
        )
        matched_alias = ranked_aliases[0]
        return IdentityResolutionResult(
            resolved=True,
            entity_id=matched_alias.player_id,
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
        suggestions=suggest_player_aliases(
            session,
            raw_name,
            team_id_context=team_id_context,
            club_id_context=club_id_context,
            limit=5,
        ),
    )


def require_player_id(
    session: Session,
    raw_name: str,
    team_id_context: int | None = None,
    club_id_context: int | None = None,
    source_id: int | None = None,
) -> int:
    resolution = resolve_player_id(
        session,
        raw_name,
        team_id_context=team_id_context,
        club_id_context=club_id_context,
        source_id=source_id,
    )
    if not resolution.resolved or resolution.entity_id is None:
        raise ValueError(f"Could not resolve player alias: {raw_name}")
    return resolution.entity_id

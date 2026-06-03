import re
import unicodedata

_APOSTROPHES_RE = re.compile(r"[\'`´‘’‚‛ʹʻʼ]")
_DASHES_RE = re.compile(r"[-‐‑‒–—―]+")
_DOTS_RE = re.compile(r"\.+")
_WHITESPACE_RE = re.compile(r"\s+")


def normalize_text(value: str) -> str:
    """Return a stable normalized representation for identity matching."""
    normalized = unicodedata.normalize("NFKD", value.strip().lower())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = _APOSTROPHES_RE.sub("", normalized)
    normalized = _DASHES_RE.sub(" ", normalized)
    normalized = _DOTS_RE.sub("", normalized)
    normalized = _WHITESPACE_RE.sub(" ", normalized)
    return normalized.strip()


def normalize_team_name(value: str) -> str:
    return normalize_text(value)


def normalize_player_name(value: str) -> str:
    return normalize_text(value)


def normalize_competition_name(value: str) -> str:
    return normalize_text(value)


def normalize_venue_name(value: str) -> str:
    return normalize_text(value)

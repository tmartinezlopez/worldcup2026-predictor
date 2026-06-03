from src.identity.normalizers import (
    normalize_player_name,
    normalize_team_name,
    normalize_text,
)


def test_normalize_text_removes_accents_and_weird_apostrophes():
    assert normalize_text("Côte d’Ivoire") == "cote divoire"


def test_normalize_player_name_removes_points():
    assert normalize_player_name("K. Mbappé") == "k mbappe"


def test_normalize_team_name_collapses_spaces():
    assert normalize_team_name("  United   States  ") == "united states"


def test_normalize_text_normalizes_hyphens():
    assert normalize_text("South-Korea") == "south korea"

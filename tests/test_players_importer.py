from src.ingestion.importers.players_importer import normalize_player_record, run
from src.staging import paths
from src.staging.jsonl import read_jsonl


def test_normalize_player_record():
    record = normalize_player_record({"full_name": "Kylian Mbappe"})

    assert record["entity_type"] == "player"
    assert record["full_name"] == "Kylian Mbappe"


def test_players_importer_requires_full_name(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "STAGING_ROOT", tmp_path / "imports")
    input_path = tmp_path / "players.csv"
    input_path.write_text(
        "full_name,team,club\nKylian Mbappe,France,Real Madrid\n,,Barcelona\n",
        encoding="utf-8",
    )

    run_dir = run(input_path)
    rejected = read_jsonl(run_dir / "rejected.jsonl")

    assert len(rejected) == 1
    assert rejected[0]["record"]["club"] == "Barcelona"

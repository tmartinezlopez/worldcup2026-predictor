from src.ingestion.source_registry import (
    load_source_registry,
    save_source_registry,
    upsert_source_entry,
)


def test_load_registry_empty_if_missing(tmp_path):
    assert load_source_registry(str(tmp_path / "missing.json")) == []


def test_save_and_load_registry(tmp_path):
    path = tmp_path / "registry.json"
    save_source_registry([{"source_name": "a"}], str(path))

    assert load_source_registry(str(path)) == [{"source_name": "a"}]


def test_upsert_updates_existing_entry(tmp_path):
    path = tmp_path / "registry.json"
    save_source_registry([{"source_name": "a", "status": "old"}], str(path))

    upsert_source_entry({"source_name": "a", "status": "new"}, str(path))

    assert load_source_registry(str(path)) == [{"source_name": "a", "status": "new"}]


def test_upsert_adds_new_entry(tmp_path):
    path = tmp_path / "registry.json"
    upsert_source_entry({"source_name": "a", "status": "new"}, str(path))

    assert load_source_registry(str(path)) == [{"source_name": "a", "status": "new"}]

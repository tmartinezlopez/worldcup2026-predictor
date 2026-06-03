import json

from src.ingestion.importers.base import (
    load_records,
    load_records_from_csv,
    load_records_from_json,
    load_records_from_jsonl,
    normalize_bool,
)


def test_load_records_from_csv(tmp_path):
    path = tmp_path / "records.csv"
    path.write_text("name,value\nA,1\n", encoding="utf-8")

    records = load_records_from_csv(path)

    assert records == [{"name": "A", "value": "1"}]


def test_load_records_from_json(tmp_path):
    path = tmp_path / "records.json"
    path.write_text(json.dumps([{"name": "A"}]), encoding="utf-8")

    assert load_records_from_json(path) == [{"name": "A"}]


def test_load_records_from_jsonl(tmp_path):
    path = tmp_path / "records.jsonl"
    path.write_text('{"name": "A"}\n{"name": "B"}\n', encoding="utf-8")

    assert load_records_from_jsonl(path) == [{"name": "A"}, {"name": "B"}]


def test_load_records_unsupported_extension(tmp_path):
    path = tmp_path / "records.txt"
    path.write_text("invalid", encoding="utf-8")

    try:
        load_records(path)
    except ValueError as exc:
        assert "Unsupported input extension" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unsupported extension")


def test_normalize_bool():
    assert normalize_bool("yes") is True
    assert normalize_bool("0") is False

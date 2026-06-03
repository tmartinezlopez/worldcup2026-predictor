from src.staging.jsonl import append_jsonl, read_jsonl, write_jsonl


def test_write_and_read_jsonl(tmp_path):
    path = tmp_path / "records.jsonl"
    records = [{"a": 1}, {"b": 2}]

    write_jsonl(path, records)

    assert read_jsonl(path) == records


def test_append_jsonl(tmp_path):
    path = tmp_path / "records.jsonl"

    append_jsonl(path, {"a": 1})
    append_jsonl(path, {"b": 2})

    assert read_jsonl(path) == [{"a": 1}, {"b": 2}]

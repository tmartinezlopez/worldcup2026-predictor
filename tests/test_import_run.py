from src.ingestion.import_run import create_import_run, finalize_import_run
from src.staging import paths
from src.staging.metadata import load_metadata
from src.validation.dataset_validator import DatasetValidator


def test_finalize_import_run_creates_expected_files(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "STAGING_ROOT", tmp_path / "imports")

    run_dir = create_import_run("test_source", "test")
    normalized_records = [
        {"row_id": 1, "match_id": "m1", "team": "USA", "metric_value": 1},
        {"row_id": 2, "match_id": "m2", "metric_value": -1},
    ]
    validator = DatasetValidator(
        required_fields=["match_id", "team", "metric_value"],
        duplicate_key_fields=["match_id", "team"],
    )
    valid_records, rejected_records, validation_result = validator.validate(
        normalized_records
    )

    finalize_import_run(
        run_dir,
        normalized_records,
        valid_records,
        rejected_records,
        validation_result,
    )

    expected_files = [
        "normalized.jsonl",
        "valid.jsonl",
        "rejected.jsonl",
        "validation_report.json",
        "review_report.md",
        "metadata.json",
    ]
    for filename in expected_files:
        assert (run_dir / filename).is_file()

    metadata = load_metadata(run_dir)
    assert metadata["source_name"] == "test_source"
    assert metadata["row_count"] == 2

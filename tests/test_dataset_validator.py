from src.validation.dataset_validator import DatasetValidator


def test_validator_separates_valid_and_rejected_records():
    validator = DatasetValidator(
        required_fields=["match_id", "team"],
        duplicate_key_fields=["match_id", "team"],
    )

    valid, rejected, result = validator.validate(
        [
            {"row_id": 1, "match_id": "m1", "team": "USA"},
            {"row_id": 2, "match_id": "m2"},
        ]
    )

    assert len(valid) == 1
    assert len(rejected) == 1
    assert result.rows_valid == 1
    assert result.rows_rejected == 1
    assert "validation_errors" in rejected[0]


def test_validator_status_passed():
    validator = DatasetValidator(required_fields=["match_id"])
    _, _, result = validator.validate([{"row_id": 1, "match_id": "m1"}])

    assert result.status == "passed"


def test_validator_status_passed_with_warnings():
    validator = DatasetValidator(required_fields=["match_id"])
    _, _, result = validator.validate(
        [
            {"row_id": 1, "match_id": "m1"},
            {"row_id": 2},
            {"row_id": 3, "match_id": "m3"},
            {"row_id": 4, "match_id": "m4"},
            {"row_id": 5, "match_id": "m5"},
            {"row_id": 6, "match_id": "m6"},
            {"row_id": 7, "match_id": "m7"},
            {"row_id": 8, "match_id": "m8"},
            {"row_id": 9, "match_id": "m9"},
            {"row_id": 10, "match_id": "m10"},
            {"row_id": 11, "match_id": "m11"},
            {"row_id": 12, "match_id": "m12"},
            {"row_id": 13, "match_id": "m13"},
            {"row_id": 14, "match_id": "m14"},
            {"row_id": 15, "match_id": "m15"},
            {"row_id": 16, "match_id": "m16"},
            {"row_id": 17, "match_id": "m17"},
            {"row_id": 18, "match_id": "m18"},
            {"row_id": 19, "match_id": "m19"},
            {"row_id": 20, "match_id": "m20"},
            {"row_id": 21, "match_id": "m21"},
        ]
    )

    assert result.status == "passed_with_warnings"


def test_validator_status_needs_review():
    validator = DatasetValidator(required_fields=["match_id"])
    _, _, result = validator.validate(
        [
            {"row_id": 1, "match_id": "m1"},
            {"row_id": 2},
            {"row_id": 3, "match_id": "m3"},
            {"row_id": 4, "match_id": "m4"},
            {"row_id": 5, "match_id": "m5"},
        ]
    )

    assert result.status == "needs_review"


def test_validator_status_blocked():
    validator = DatasetValidator(required_fields=["match_id"])
    _, _, result = validator.validate(
        [
            {"row_id": 1},
            {"row_id": 2},
            {"row_id": 3},
            {"row_id": 4, "match_id": "m4"},
        ]
    )

    assert result.status == "blocked"


def test_rejected_records_include_validation_errors():
    validator = DatasetValidator(required_fields=["metric_value"])
    _, rejected, _ = validator.validate([{"row_id": 1, "metric_value": -2}])

    assert rejected[0]["validation_errors"][0]["code"] == "negative_value"

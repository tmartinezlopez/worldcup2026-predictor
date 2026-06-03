from datetime import date, timedelta

from src.validation.common_checks import (
    check_no_future_date,
    check_non_negative_number,
    check_probability_range,
    check_required_fields,
    check_valid_date,
    detect_duplicates,
)


def test_required_field_missing():
    issues = check_required_fields({"a": 1}, ["a", "b"], row_id=1)

    assert len(issues) == 1
    assert issues[0].code == "missing_required_field"


def test_non_negative_check():
    issues = check_non_negative_number({"value": -1}, ["value"], row_id=1)

    assert len(issues) == 1
    assert issues[0].code == "negative_value"


def test_probability_range():
    issues = check_probability_range({"p_win": 1.2}, ["p_win"], row_id=1)

    assert len(issues) == 1
    assert issues[0].code == "probability_out_of_range"


def test_valid_date():
    assert check_valid_date({"match_date": "2026-06-01"}, "match_date", row_id=1) == []


def test_future_date():
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    issues = check_no_future_date(
        {"match_date": tomorrow},
        "match_date",
        row_id=1,
        cutoff_date=date.today(),
    )

    assert len(issues) == 1
    assert issues[0].code == "future_date"


def test_detect_duplicates():
    issues = detect_duplicates(
        [
            {"row_id": 1, "match_id": "m1", "team": "USA"},
            {"row_id": 2, "match_id": "m1", "team": "USA"},
        ],
        ["match_id", "team"],
    )

    assert len(issues) == 1
    assert issues[0].code == "duplicate_record"

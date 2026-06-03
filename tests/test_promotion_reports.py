import json

from src.ingestion.promotion.reports import (
    build_promotion_report,
    write_promotion_markdown,
    write_promotion_report,
)


def test_build_promotion_report():
    report = build_promotion_report(
        run_dir="/tmp/run",
        entity_type="historical_results",
        dry_run=True,
        rows_read=3,
        rows_promoted=2,
        rows_skipped=1,
        teams_created=0,
        competitions_created=1,
        matches_created=2,
        matches_updated=0,
        unresolved_teams=[],
        errors=[],
    )

    assert report["status"] == "dry_run_passed"
    assert report["rows_promoted"] == 2


def test_write_promotion_json_and_markdown(tmp_path):
    report = build_promotion_report(
        run_dir=str(tmp_path),
        entity_type="historical_results",
        dry_run=False,
        rows_read=1,
        rows_promoted=1,
        rows_skipped=0,
        teams_created=0,
        competitions_created=0,
        matches_created=1,
        matches_updated=0,
        unresolved_teams=[],
        errors=[],
    )

    json_path = write_promotion_report(tmp_path, report)
    md_path = write_promotion_markdown(tmp_path, report)

    assert json.loads(json_path.read_text(encoding="utf-8"))["status"] == "promoted"
    assert "Promotion Report" in md_path.read_text(encoding="utf-8")

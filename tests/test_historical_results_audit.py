import json
import urllib.error

from src.ingestion.source_audits.historical_results_audit import (
    audit_historical_results_source,
    download_to_temp_file,
)
from src.staging import paths


def test_audit_with_local_file_works(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "STAGING_ROOT", tmp_path / "imports")
    input_path = tmp_path / "results.csv"
    input_path.write_text(
        "date,home_team,away_team,home_score,away_score,tournament\n"
        "2024-01-01,Spain,Italy,2,1,Friendly\n",
        encoding="utf-8",
    )

    run_dir = audit_historical_results_source(
        local_file=input_path,
        max_rows=1,
        no_download=True,
    )

    assert (run_dir / "source_audit_report.json").is_file()
    assert (run_dir / "source_audit_report.md").is_file()


def test_max_rows_limits_rows(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "STAGING_ROOT", tmp_path / "imports")
    input_path = tmp_path / "results.csv"
    input_path.write_text(
        "date,home_team,away_team,home_score,away_score,tournament\n"
        "2024-01-01,Spain,Italy,2,1,Friendly\n"
        "2024-01-02,France,Germany,1,0,Friendly\n",
        encoding="utf-8",
    )

    run_dir = audit_historical_results_source(
        local_file=input_path,
        max_rows=1,
        no_download=True,
    )
    report = json.loads(
        (run_dir / "source_audit_report.json").read_text(encoding="utf-8")
    )

    assert report["rows_read"] == 1
    assert report["partial_audit"] is True


def test_report_includes_date_range(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "STAGING_ROOT", tmp_path / "imports")
    input_path = tmp_path / "results.csv"
    input_path.write_text(
        "date,home_team,away_team,home_score,away_score,tournament\n"
        "2024-01-01,Spain,Italy,2,1,Friendly\n"
        "2024-01-02,France,Germany,1,0,Friendly\n",
        encoding="utf-8",
    )

    run_dir = audit_historical_results_source(local_file=input_path, no_download=True)
    report = json.loads(
        (run_dir / "source_audit_report.json").read_text(encoding="utf-8")
    )

    assert report["date_min"] == "2024-01-01"
    assert report["date_max"] == "2024-01-02"


def test_no_download_without_local_file_fails_clear():
    try:
        audit_historical_results_source(no_download=True)
    except ValueError as exc:
        assert "provide --local-file" in str(exc)
    else:
        raise AssertionError("Expected ValueError when no input source is available")


def test_download_failure_is_clear(monkeypatch):
    def fake_urlopen(_url):
        raise urllib.error.URLError("network down")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    try:
        download_to_temp_file("https://example.com/results.csv")
    except RuntimeError as exc:
        assert "Failed to download source" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError on failed download")

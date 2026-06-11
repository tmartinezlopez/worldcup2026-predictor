import json
from pathlib import Path

import pytest

from src.dashboard.static_dashboard import DashboardBuildError, build_static_dashboard


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_static_dashboard_generates_html_and_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_text(
        tmp_path / "data/processed/final_reports/GROUP_STAGE_MD1/batch_report.json",
        json.dumps(
            {
                "batch_code": "GROUP_STAGE_MD1",
                "generated_at": "2026-06-11T10:00:00+00:00",
                "summary": {
                    "total_matches": 1,
                    "predictions_included": 1,
                    "official_predictions": 1,
                    "draft_predictions": 0,
                },
                "warnings": ["draft fallback not used"],
            }
        ),
    )
    _write_text(
        tmp_path / "data/processed/final_reports/GROUP_STAGE_MD1/predictions.csv",
        (
            "match_id,batch_code,date,competition,stage,team_a,team_b,"
            "p_team_a_win_90,p_draw_90,p_team_b_win_90,predicted_outcome\n"
            "2,GROUP_STAGE_MD1,2026-06-12,FIFA World Cup,Group Stage,"
            "United States,Mexico,1.0,0.0,0.0,team_a_win\n"
        ),
    )
    _write_text(
        tmp_path
        / "data/processed/simulation_reports/GROUP_STAGE_MD1/simulation_results.csv",
        (
            "team_id,team_name,expected_points,average_rank\n"
            "3,United States,3.0,1.0\n"
        ),
    )

    report = build_static_dashboard(
        batch_code="GROUP_STAGE_MD1",
        include_simulation=True,
        output_dir=tmp_path / "data/processed/dashboard",
        title="World Cup 2026 Predictor",
    )

    html_path = Path(report["dashboard_html"])
    json_path = Path(report["dashboard_json"])

    assert html_path.is_file()
    assert json_path.is_file()
    content = html_path.read_text(encoding="utf-8")
    data = json.loads(json_path.read_text(encoding="utf-8"))

    assert "World Cup 2026 Predictor" in content
    assert "GROUP_STAGE_MD1" in content
    assert "Predictions" in content
    assert "Simulation" in content
    assert "Batch snapshot" in content
    assert "summary-grid" in content
    assert "1X2 probabilities" in content
    assert "prob-track" in content
    assert "Output files" in content
    assert "United States" in content
    assert data["batch_code"] == "GROUP_STAGE_MD1"
    assert len(data["predictions_rows"]) == 1
    assert len(data["simulation_rows"]) == 1
    assert len(data["summary_cards"]) == 4
    assert data["status_badge"]["label"] == "Official"


def test_static_dashboard_works_without_simulation_when_not_requested(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    _write_text(
        tmp_path / "data/processed/final_reports/GROUP_STAGE_MD1/batch_report.json",
        json.dumps(
            {
                "batch_code": "GROUP_STAGE_MD1",
                "generated_at": "2026-06-11T10:00:00+00:00",
                "summary": {
                    "total_matches": 1,
                    "predictions_included": 1,
                    "official_predictions": 0,
                    "draft_predictions": 1,
                },
                "warnings": [],
            }
        ),
    )
    _write_text(
        tmp_path / "data/processed/final_reports/GROUP_STAGE_MD1/predictions.csv",
        "match_id,batch_code\n2,GROUP_STAGE_MD1\n",
    )

    report = build_static_dashboard(
        batch_code="GROUP_STAGE_MD1",
        include_simulation=False,
        output_dir=tmp_path / "data/processed/dashboard",
    )

    content = Path(report["dashboard_html"]).read_text(encoding="utf-8")
    data = json.loads(Path(report["dashboard_json"]).read_text(encoding="utf-8"))

    assert "Simulation data not included." in content
    assert "Hackathon Demo Dashboard" in content
    assert "Output files" in content
    assert data["simulation_rows"] == []
    assert data["status_badge"]["label"] == "Draft"


def test_static_dashboard_raises_clear_error_when_batch_report_is_missing(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)

    with pytest.raises(DashboardBuildError, match="missing required artifact"):
        build_static_dashboard(
            batch_code="GROUP_STAGE_MD1",
            output_dir=tmp_path / "data/processed/dashboard",
        )

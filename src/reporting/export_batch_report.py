"""Export a lightweight final report for one batch."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.connection import get_session
from src.db.models import (
    Batch,
    BatchMatch,
    Competition,
    FeatureSet,
    Match,
    ModelRun,
    Prediction,
    Team,
)

DEFAULT_OUTPUT_DIR = Path("data/processed/final_reports")
SIMULATION_REPORTS_ROOT = Path("data/processed/simulation_reports")


def _ensure_utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    else:
        value = value.astimezone(UTC)
    return value.isoformat()


def _load_reference_map(session: Session, model, ids: set[int]) -> dict[int, Any]:
    if not ids:
        return {}
    return {
        item.id: item
        for item in session.scalars(
            select(model).where(model.id.in_(sorted(ids)))
        ).all()
    }


def _prediction_priority(prediction: Prediction) -> tuple[int, int, datetime, int]:
    predicted_at = prediction.predicted_at
    if predicted_at.tzinfo is None:
        predicted_at = predicted_at.replace(tzinfo=UTC)
    else:
        predicted_at = predicted_at.astimezone(UTC)
    return (
        1 if prediction.is_official or prediction.is_frozen else 0,
        1 if prediction.is_frozen else 0,
        predicted_at,
        prediction.id,
    )


def _select_predictions_for_matches(
    predictions_by_match: dict[int, list[Prediction]],
    *,
    official_only: bool,
    include_drafts: bool,
) -> tuple[dict[int, Prediction], list[str]]:
    warnings: list[str] = []
    selected: dict[int, Prediction] = {}
    for match_id, predictions in predictions_by_match.items():
        ordered = sorted(predictions, key=_prediction_priority, reverse=True)
        official_predictions = [
            item for item in ordered if item.is_official or item.is_frozen
        ]
        if official_predictions:
            selected[match_id] = official_predictions[0]
            continue
        if official_only:
            continue
        if include_drafts:
            selected[match_id] = ordered[0]

    if selected and all(
        not prediction.is_official and not prediction.is_frozen
        for prediction in selected.values()
    ):
        warnings.append("only draft predictions were available for this batch")
    return selected, warnings


def _prediction_row(
    *,
    match: Match,
    batch: Batch,
    prediction: Prediction | None,
    teams: dict[int, Team],
    competitions: dict[int, Competition],
    model_runs: dict[int, ModelRun],
    feature_sets: dict[int, FeatureSet],
) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    team_a = teams.get(match.team_a_id)
    team_b = teams.get(match.team_b_id)
    competition = (
        competitions.get(match.competition_id) if match.competition_id else None
    )
    model_run = (
        model_runs.get(prediction.model_run_id)
        if prediction is not None and prediction.model_run_id is not None
        else None
    )
    feature_set = None
    if prediction is not None and prediction.feature_set_id is not None:
        feature_set = feature_sets.get(prediction.feature_set_id)
    elif model_run is not None and model_run.feature_set_id is not None:
        feature_set = feature_sets.get(model_run.feature_set_id)

    if team_a is None or team_b is None:
        warnings.append(f"match_id={match.id} has missing team references")
    if competition is None:
        warnings.append(f"match_id={match.id} has missing competition reference")

    row = {
        "match_id": match.id,
        "batch_code": batch.code,
        "date": match.date.isoformat() if match.date is not None else None,
        "competition": competition.name if competition is not None else None,
        "stage": match.stage,
        "team_a": team_a.name if team_a is not None else None,
        "team_b": team_b.name if team_b is not None else None,
        "p_team_a_win_90": (
            prediction.p_team_a_win_90 if prediction is not None else None
        ),
        "p_draw_90": prediction.p_draw_90 if prediction is not None else None,
        "p_team_b_win_90": (
            prediction.p_team_b_win_90 if prediction is not None else None
        ),
        "predicted_outcome": (
            prediction.predicted_outcome if prediction is not None else None
        ),
        "predicted_score_a": (
            prediction.predicted_score_a if prediction is not None else None
        ),
        "predicted_score_b": (
            prediction.predicted_score_b if prediction is not None else None
        ),
        "model_name": model_run.model_name if model_run is not None else None,
        "model_run_id": model_run.id if model_run is not None else None,
        "feature_set_id": feature_set.id if feature_set is not None else None,
        "is_official": prediction.is_official if prediction is not None else None,
        "is_frozen": prediction.is_frozen if prediction is not None else None,
        "confidence_label": (
            prediction.confidence_label if prediction is not None else None
        ),
    }
    return row, warnings


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "match_id",
        "batch_code",
        "date",
        "competition",
        "stage",
        "team_a",
        "team_b",
        "p_team_a_win_90",
        "p_draw_90",
        "p_team_b_win_90",
        "predicted_outcome",
        "predicted_score_a",
        "predicted_score_b",
        "model_name",
        "model_run_id",
        "feature_set_id",
        "is_official",
        "is_frozen",
        "confidence_label",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _load_simulation_summary(batch_code: str) -> list[dict[str, str]]:
    csv_path = SIMULATION_REPORTS_ROOT / batch_code / "simulation_results.csv"
    if not csv_path.is_file():
        return []
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_markdown(path: Path, report: dict[str, Any]) -> None:
    lines = [
        f"# Batch Report: {report['batch_code']}",
        "",
        f"- Cutoff time: `{report['cutoff_time']}`",
        f"- Generated at: `{report['generated_at']}`",
        "",
        "## Summary",
        f"- Total matches: {report['summary']['total_matches']}",
        f"- Predictions included: {report['summary']['predictions_included']}",
        f"- Official predictions: {report['summary']['official_predictions']}",
        f"- Draft predictions: {report['summary']['draft_predictions']}",
        "",
        "## Predictions",
        "",
        (
            "| Date | Competition | Stage | Team A | Team B | P(A) | P(D) | P(B) "
            "| Outcome | Score | Model | Model Run | Official | Frozen | Confidence |"
        ),
        (
            "| --- | --- | --- | --- | --- | ---: | ---: | ---: | --- | --- "
            "| --- | ---: | --- | --- | --- |"
        ),
    ]
    for row in report["predictions"]:
        score = "-"
        if (
            row["predicted_score_a"] is not None
            and row["predicted_score_b"] is not None
        ):
            score = f"{row['predicted_score_a']}-{row['predicted_score_b']}"
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["date"] or "-"),
                    str(row["competition"] or "-"),
                    str(row["stage"] or "-"),
                    str(row["team_a"] or "-"),
                    str(row["team_b"] or "-"),
                    str(row["p_team_a_win_90"] or "-"),
                    str(row["p_draw_90"] or "-"),
                    str(row["p_team_b_win_90"] or "-"),
                    str(row["predicted_outcome"] or "-"),
                    score,
                    str(row["model_name"] or "-"),
                    str(row["model_run_id"] or "-"),
                    str(
                        row["is_official"]
                        if row["is_official"] is not None
                        else "-"
                    ),
                    str(row["is_frozen"] if row["is_frozen"] is not None else "-"),
                    str(row["confidence_label"] or "-"),
                ]
            )
            + " |"
        )
    lines.extend(["", "## Warnings"])
    if report["warnings"]:
        lines.extend(f"- {warning}" for warning in report["warnings"])
    else:
        lines.append("- None.")
    if report["simulation_summary"]:
        lines.extend(
            [
                "",
                "## Simulation Summary",
                "",
                (
                    "| Team | Expected Points | Average Rank | P(Top) | P(Bottom) | "
                    "Wins Avg | Draws Avg | Losses Avg |"
                ),
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for row in report["simulation_summary"]:
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(row.get("team_name") or "-"),
                        str(row.get("expected_points") or "-"),
                        str(row.get("average_rank") or "-"),
                        str(row.get("probability_top_batch") or "-"),
                        str(row.get("probability_bottom_batch") or "-"),
                        str(row.get("simulated_wins_avg") or "-"),
                        str(row.get("simulated_draws_avg") or "-"),
                        str(row.get("simulated_losses_avg") or "-"),
                    ]
                )
                + " |"
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_html(path: Path, report: dict[str, Any]) -> None:
    rows_html = []
    for row in report["predictions"]:
        score = "-"
        if (
            row["predicted_score_a"] is not None
            and row["predicted_score_b"] is not None
        ):
            score = f"{row['predicted_score_a']}-{row['predicted_score_b']}"
        cells = [
            row["date"] or "-",
            row["competition"] or "-",
            row["stage"] or "-",
            row["team_a"] or "-",
            row["team_b"] or "-",
            row["p_team_a_win_90"] if row["p_team_a_win_90"] is not None else "-",
            row["p_draw_90"] if row["p_draw_90"] is not None else "-",
            row["p_team_b_win_90"] if row["p_team_b_win_90"] is not None else "-",
            row["predicted_outcome"] or "-",
            score,
            row["model_name"] or "-",
            row["model_run_id"] if row["model_run_id"] is not None else "-",
            row["is_official"] if row["is_official"] is not None else "-",
            row["is_frozen"] if row["is_frozen"] is not None else "-",
            row["confidence_label"] or "-",
        ]
        rows_html.append(
            "<tr>"
            + "".join(f"<td>{escape(str(cell))}</td>" for cell in cells)
            + "</tr>"
        )

    warnings_html = "".join(
        f"<li>{escape(warning)}</li>" for warning in report["warnings"]
    ) or "<li>None.</li>"
    simulation_rows_html = ""
    if report["simulation_summary"]:
        simulation_rows_html = "".join(
            (
                "<tr>"
                f"<td>{escape(str(row.get('team_name') or '-'))}</td>"
                f"<td>{escape(str(row.get('expected_points') or '-'))}</td>"
                f"<td>{escape(str(row.get('average_rank') or '-'))}</td>"
                f"<td>{escape(str(row.get('probability_top_batch') or '-'))}</td>"
                f"<td>{escape(str(row.get('probability_bottom_batch') or '-'))}</td>"
                f"<td>{escape(str(row.get('simulated_wins_avg') or '-'))}</td>"
                f"<td>{escape(str(row.get('simulated_draws_avg') or '-'))}</td>"
                f"<td>{escape(str(row.get('simulated_losses_avg') or '-'))}</td>"
                "</tr>"
            )
            for row in report["simulation_summary"]
        )
    simulation_section_html = ""
    if report["simulation_summary"]:
        simulation_section_html = (
            "<h2>Simulation Summary</h2>"
            "<table><thead><tr><th>Team</th><th>Expected Points</th>"
            "<th>Average Rank</th><th>P(Top)</th><th>P(Bottom)</th>"
            "<th>Wins Avg</th><th>Draws Avg</th><th>Losses Avg</th>"
            "</tr></thead><tbody>"
            + simulation_rows_html
            + "</tbody></table>"
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Batch Report: {escape(report["batch_code"])}</title>
  <style>
    body {{ font-family: Georgia, serif; margin: 2rem; color: #1e1e1e; }}
    h1, h2 {{ margin-bottom: 0.5rem; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 1rem; }}
    th, td {{ border: 1px solid #cfcfcf; padding: 0.55rem; text-align: left; }}
    th {{ background: #f2f2f2; }}
    .meta, .summary {{ margin: 0 0 1rem 0; }}
    .summary li, .warnings li {{ margin: 0.2rem 0; }}
  </style>
</head>
<body>
  <h1>Batch Report: {escape(report["batch_code"])}</h1>
  <p class="meta"><strong>Cutoff time:</strong>
  {escape(str(report["cutoff_time"]))}<br />
  <strong>Generated at:</strong> {escape(str(report["generated_at"]))}</p>
  <h2>Summary</h2>
  <ul class="summary">
    <li>Total matches: {report["summary"]["total_matches"]}</li>
    <li>Predictions included: {report["summary"]["predictions_included"]}</li>
    <li>Official predictions: {report["summary"]["official_predictions"]}</li>
    <li>Draft predictions: {report["summary"]["draft_predictions"]}</li>
  </ul>
  <h2>Predictions</h2>
  <table>
    <thead>
      <tr>
        <th>Date</th><th>Competition</th><th>Stage</th><th>Team A</th><th>Team B</th>
        <th>P(A)</th><th>P(D)</th><th>P(B)</th><th>Outcome</th><th>Score</th>
        <th>Model</th><th>Model Run</th><th>Official</th><th>Frozen</th>
        <th>Confidence</th>
      </tr>
    </thead>
    <tbody>
      {''.join(rows_html)}
    </tbody>
  </table>
  <h2>Warnings</h2>
  <ul class="warnings">{warnings_html}</ul>
  {simulation_section_html}
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")


def export_batch_report(
    session: Session,
    *,
    batch_code: str,
    official_only: bool = False,
    include_drafts: bool = False,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    batch = session.scalar(select(Batch).where(Batch.code == batch_code))
    if batch is None:
        raise ValueError(f"unknown batch code: {batch_code}")

    batch_matches = session.scalars(
        select(BatchMatch)
        .where(BatchMatch.batch_id == batch.id)
        .order_by(BatchMatch.order_in_batch)
    ).all()
    match_ids = [item.match_id for item in batch_matches]
    matches = (
        session.scalars(
            select(Match)
            .where(Match.id.in_(match_ids))
            .order_by(Match.date, Match.kickoff_time, Match.id)
        ).all()
        if match_ids
        else []
    )
    match_map = {match.id: match for match in matches}
    ordered_matches = [
        match_map[item.match_id]
        for item in batch_matches
        if item.match_id in match_map
    ]

    predictions = session.scalars(
        select(Prediction)
        .where(Prediction.batch_id == batch.id)
        .order_by(Prediction.match_id, Prediction.id)
    ).all()
    predictions_by_match: dict[int, list[Prediction]] = {}
    for prediction in predictions:
        predictions_by_match.setdefault(prediction.match_id, []).append(prediction)

    selected_predictions, warnings = _select_predictions_for_matches(
        predictions_by_match,
        official_only=official_only,
        include_drafts=include_drafts,
    )

    team_ids = {match.team_a_id for match in ordered_matches} | {
        match.team_b_id for match in ordered_matches
    }
    competition_ids = {
        match.competition_id
        for match in ordered_matches
        if match.competition_id is not None
    }
    model_run_ids = {
        prediction.model_run_id
        for prediction in selected_predictions.values()
        if prediction.model_run_id is not None
    }
    feature_set_ids = {
        prediction.feature_set_id
        for prediction in selected_predictions.values()
        if prediction.feature_set_id is not None
    }

    teams = _load_reference_map(session, Team, team_ids)
    competitions = _load_reference_map(session, Competition, competition_ids)
    model_runs = _load_reference_map(session, ModelRun, model_run_ids)
    feature_sets = _load_reference_map(session, FeatureSet, feature_set_ids)
    feature_set_ids_from_runs = {
        run.feature_set_id
        for run in model_runs.values()
        if run.feature_set_id is not None
    }
    feature_sets.update(
        _load_reference_map(
            session,
            FeatureSet,
            feature_set_ids_from_runs - set(feature_sets.keys()),
        )
    )

    prediction_rows: list[dict[str, Any]] = []
    for match in ordered_matches:
        prediction = selected_predictions.get(match.id)
        row, row_warnings = _prediction_row(
            match=match,
            batch=batch,
            prediction=prediction,
            teams=teams,
            competitions=competitions,
            model_runs=model_runs,
            feature_sets=feature_sets,
        )
        if prediction is not None:
            prediction_rows.append(row)
        warnings.extend(row_warnings)

    if not prediction_rows:
        warnings.append("no predictions were available for this batch")

    summary = {
        "total_matches": len(ordered_matches),
        "predictions_included": len(prediction_rows),
        "official_predictions": sum(
            1
            for row in prediction_rows
            if row["is_official"] or row["is_frozen"]
        ),
        "draft_predictions": sum(
            1
            for row in prediction_rows
            if row["is_official"] is False and row["is_frozen"] is False
        ),
    }

    generated_at = datetime.now(UTC).isoformat()
    simulation_summary = _load_simulation_summary(batch.code)
    report = {
        "batch_code": batch.code,
        "cutoff_time": _ensure_utc(batch.cutoff_time),
        "generated_at": generated_at,
        "summary": summary,
        "predictions": prediction_rows,
        "simulation_summary": simulation_summary,
        "warnings": sorted(set(warnings)),
        "options": {
            "official_only": official_only,
            "include_drafts": include_drafts,
        },
    }

    output_root = output_dir or DEFAULT_OUTPUT_DIR
    batch_dir = output_root / batch.code
    batch_dir.mkdir(parents=True, exist_ok=True)
    (batch_dir / "batch_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    _write_markdown(batch_dir / "batch_report.md", report)
    _write_html(batch_dir / "batch_report.html", report)
    _write_csv(batch_dir / "predictions.csv", prediction_rows)
    report["output_dir"] = str(batch_dir)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export a final batch report")
    parser.add_argument("--batch-code", required=True)
    parser.add_argument("--official-only", action="store_true")
    parser.add_argument("--include-drafts", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with get_session() as session:
        report = export_batch_report(
            session,
            batch_code=args.batch_code,
            official_only=args.official_only,
            include_drafts=args.include_drafts,
            output_dir=args.output_dir,
        )
    print(f"batch_code={report['batch_code']}")
    print(f"predictions_included={report['summary']['predictions_included']}")
    print(f"output_dir={report['output_dir']}")


if __name__ == "__main__":
    main()

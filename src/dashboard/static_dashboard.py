"""Generate a static HTML dashboard from existing processed artifacts."""

from __future__ import annotations

import argparse
import csv
import json
from html import escape
from pathlib import Path
from typing import Any

DEFAULT_OUTPUT_ROOT = Path("data/processed/dashboard")
FINAL_REPORTS_ROOT = Path("data/processed/final_reports")
SIMULATION_REPORTS_ROOT = Path("data/processed/simulation_reports")


class DashboardBuildError(ValueError):
    """Raised when required dashboard artifacts are missing or invalid."""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DashboardBuildError(f"missing required artifact: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DashboardBuildError(f"invalid JSON artifact: {path}") from exc


def _read_csv(path: Path) -> list[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))
    except FileNotFoundError as exc:
        raise DashboardBuildError(f"missing required artifact: {path}") from exc


def _artifact_paths(batch_code: str) -> dict[str, Path]:
    final_root = FINAL_REPORTS_ROOT / batch_code
    simulation_root = SIMULATION_REPORTS_ROOT / batch_code
    return {
        "batch_report_json": final_root / "batch_report.json",
        "predictions_csv": final_root / "predictions.csv",
        "batch_report_html": final_root / "batch_report.html",
        "simulation_csv": simulation_root / "simulation_results.csv",
    }


def _link_item(label: str, path: Path, *, required: bool) -> dict[str, Any]:
    return {
        "label": label,
        "path": str(path),
        "exists": path.is_file(),
        "required": required,
    }


def _summary_cards(report: dict[str, Any]) -> list[dict[str, Any]]:
    summary = report.get("summary") or {}
    return [
        {
            "label": "Total Matches",
            "value": summary.get("total_matches", 0),
            "tone": "navy",
        },
        {
            "label": "Predictions Included",
            "value": summary.get("predictions_included", 0),
            "tone": "teal",
        },
        {
            "label": "Official Predictions",
            "value": summary.get("official_predictions", 0),
            "tone": "green",
        },
        {
            "label": "Draft Predictions",
            "value": summary.get("draft_predictions", 0),
            "tone": "gold",
        },
    ]


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_probability(value: Any) -> str:
    numeric = _safe_float(value)
    if numeric is None:
        return "-"
    return f"{numeric * 100:.1f}%"


def _result_badge(summary: dict[str, Any]) -> dict[str, str]:
    official_count = int(summary.get("official_predictions", 0) or 0)
    draft_count = int(summary.get("draft_predictions", 0) or 0)
    if official_count > 0:
        return {"label": "Official", "tone": "official"}
    if draft_count > 0:
        return {"label": "Draft", "tone": "draft"}
    return {"label": "Demo", "tone": "demo"}


def _probability_rows(row: dict[str, Any]) -> list[dict[str, Any]]:
    options = [
        {
            "label": "1",
            "name": row.get("team_a") or "Team A",
            "value": _safe_float(row.get("p_team_a_win_90")) or 0.0,
            "tone": "home",
        },
        {
            "label": "X",
            "name": "Draw",
            "value": _safe_float(row.get("p_draw_90")) or 0.0,
            "tone": "draw",
        },
        {
            "label": "2",
            "name": row.get("team_b") or "Team B",
            "value": _safe_float(row.get("p_team_b_win_90")) or 0.0,
            "tone": "away",
        },
    ]
    best_value = max(item["value"] for item in options)
    for item in options:
        item["is_top"] = item["value"] == best_value and best_value > 0
        item["width"] = f"{item['value'] * 100:.1f}%"
        item["percent"] = f"{item['value'] * 100:.1f}%"
    return options


def _prediction_cards(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for row in rows:
        outcome = (
            str(row.get("predicted_outcome") or "unknown")
            .replace("_", " ")
            .title()
        )
        score = "-"
        if row.get("predicted_score_a") and row.get("predicted_score_b"):
            score = f"{row['predicted_score_a']}-{row['predicted_score_b']}"
        elif row.get("predicted_score_a") == 0 or row.get("predicted_score_b") == 0:
            score = (
                f"{row.get('predicted_score_a', 0)}"
                f"-{row.get('predicted_score_b', 0)}"
            )
        cards.append(
            {
                "competition": row.get("competition") or "Unknown competition",
                "stage": row.get("stage") or "Unknown stage",
                "date": row.get("date") or "-",
                "team_a": row.get("team_a") or "Team A",
                "team_b": row.get("team_b") or "Team B",
                "predicted_outcome": outcome,
                "confidence_label": row.get("confidence_label") or "n/a",
                "score": score,
                "probabilities": _probability_rows(row),
                "model_name": row.get("model_name") or "-",
                "official": bool(str(row.get("is_official")).lower() == "true"),
                "frozen": bool(str(row.get("is_frozen")).lower() == "true"),
            }
        )
    return cards


def _simulation_table(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return []

    best_points = max(_safe_float(row.get("expected_points")) or 0.0 for row in rows)
    formatted_rows = []
    for row in rows:
        expected_points = _safe_float(row.get("expected_points")) or 0.0
        top_probability = _safe_float(row.get("probability_top_batch")) or 0.0
        bottom_probability = _safe_float(row.get("probability_bottom_batch")) or 0.0
        formatted_rows.append(
            {
                "team_name": row.get("team_name") or "-",
                "expected_points": f"{expected_points:.2f}",
                "average_rank": row.get("average_rank") or "-",
                "probability_top_batch": f"{top_probability * 100:.1f}%",
                "probability_bottom_batch": f"{bottom_probability * 100:.1f}%",
                "simulated_wins_avg": row.get("simulated_wins_avg") or "-",
                "simulated_draws_avg": row.get("simulated_draws_avg") or "-",
                "simulated_losses_avg": row.get("simulated_losses_avg") or "-",
                "is_top_team": expected_points == best_points,
            }
        )
    return formatted_rows


def _artifacts_html(links: list[dict[str, Any]]) -> str:
    cards = []
    for item in links:
        status_class = "artifact-ready" if item["exists"] else "artifact-missing"
        status_label = "Ready" if item["exists"] else "Missing"
        cards.append(
            "<article class='artifact-card'>"
            f"<div class='artifact-top'><span class='artifact-status {status_class}'>"
            f"{escape(status_label)}</span></div>"
            f"<h3>{escape(item['label'])}</h3>"
            f"<p><code>{escape(item['path'])}</code></p>"
            "</article>"
        )
    return (
        "<section class='panel'>"
        "<div class='section-heading'>"
        "<span class='eyebrow'>Artifacts</span>"
        "<h2>Output files</h2>"
        "<p>Static links to the generated artifacts for this batch demo.</p>"
        "</div>"
        "<div class='artifact-grid'>"
        + "".join(cards)
        + "</div></section>"
    )


def _warnings_html(warnings: list[str]) -> str:
    if not warnings:
        return (
            "<section class='panel warnings-panel'>"
            "<div class='section-heading'>"
            "<span class='eyebrow'>Warnings</span>"
            "<h2>Quality notes</h2>"
            "</div>"
            "<p class='empty'>No warnings for this dashboard export.</p>"
            "</section>"
        )
    items = "".join(f"<li>{escape(warning)}</li>" for warning in warnings)
    return (
        "<section class='panel warnings-panel has-warnings'>"
        "<div class='section-heading'>"
        "<span class='eyebrow'>Warnings</span>"
        "<h2>Attention points</h2>"
        "</div>"
        f"<ul class='warning-list'>{items}</ul>"
        "</section>"
    )


def _predictions_html(cards: list[dict[str, Any]]) -> str:
    if not cards:
        return (
            "<section class='panel'>"
            "<div class='section-heading'><span class='eyebrow'>Predictions</span>"
            "<h2>Match outlook</h2></div>"
            "<p class='empty'>No predictions found.</p></section>"
        )

    items = []
    for card in cards:
        probability_rows = []
        for option in card["probabilities"]:
            top_class = " is-top" if option["is_top"] else ""
            probability_rows.append(
                "<div class='prob-row'>"
                f"<div class='prob-label{top_class}'>"
                f"<span class='prob-code'>{escape(option['label'])}</span>"
                f"<span>{escape(option['name'])}</span>"
                "</div>"
                "<div class='prob-track'>"
                f"<div class='prob-fill prob-{escape(option['tone'])}{top_class}' "
                f"style='width: {escape(option['width'])};'></div>"
                "</div>"
                f"<div class='prob-value{top_class}'>{escape(option['percent'])}</div>"
                "</div>"
            )

        state_badges = []
        if card["official"]:
            state_badges.append("<span class='micro-badge official'>Official</span>")
        if card["frozen"]:
            state_badges.append("<span class='micro-badge frozen'>Frozen</span>")
        state_badges.append(
            "<span class='micro-badge confidence'>"
            f"{escape(card['confidence_label'])}"
            "</span>"
        )

        items.append(
            "<article class='prediction-card'>"
            "<div class='prediction-top'>"
            f"<div><div class='prediction-meta'>{escape(card['competition'])}</div>"
            f"<h3>{escape(card['stage'])}</h3></div>"
            f"<div class='prediction-date'>{escape(card['date'])}</div>"
            "</div>"
            "<div class='matchup'>"
            f"<div class='team team-a'>{escape(card['team_a'])}</div>"
            "<div class='versus'>vs</div>"
            f"<div class='team team-b'>{escape(card['team_b'])}</div>"
            "</div>"
            "<div class='prediction-highlight'>"
            "<div class='outcome'>"
            f"Prediction: {escape(card['predicted_outcome'])}"
            "</div>"
            f"<div class='score-pill'>Projected score {escape(card['score'])}</div>"
            "</div>"
            "<div class='probability-bars'>"
            "<div class='section-mini-title'>1X2 probabilities</div>"
            + "".join(probability_rows)
            + "</div>"
            "<div class='prediction-footer'>"
            f"<span class='model-chip'>{escape(card['model_name'])}</span>"
            f"<div class='badge-row'>{''.join(state_badges)}</div>"
            "</div>"
            "</article>"
        )

    return (
        "<section class='panel'>"
        "<div class='section-heading'>"
        "<span class='eyebrow'>Predictions</span>"
        "<h2>Match outlook</h2>"
        "<p>Readable match cards with 1X2 probability bars and the strongest "
        "pick highlighted.</p>"
        "</div>"
        "<div class='prediction-grid'>"
        + "".join(items)
        + "</div></section>"
    )


def _simulation_html(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return (
            "<section class='panel'>"
            "<div class='section-heading'><span class='eyebrow'>Simulation</span>"
            "<h2>Batch scenario view</h2></div>"
            "<p class='empty'>Simulation data not included.</p></section>"
        )

    body_rows = []
    for row in rows:
        row_class = " class='top-team-row'" if row["is_top_team"] else ""
        top_badge = (
            "<span class='table-badge top-badge'>Top Team</span>"
            if row["is_top_team"]
            else ""
        )
        body_rows.append(
            f"<tr{row_class}>"
            "<td><div class='team-cell'>"
            f"{escape(row['team_name'])}{top_badge}"
            "</div></td>"
            f"<td>{escape(row['expected_points'])}</td>"
            f"<td>{escape(str(row['average_rank']))}</td>"
            "<td><span class='table-badge teal-badge'>"
            f"{escape(row['probability_top_batch'])}"
            "</span></td>"
            "<td><span class='table-badge amber-badge'>"
            f"{escape(row['probability_bottom_batch'])}"
            "</span></td>"
            f"<td>{escape(str(row['simulated_wins_avg']))}</td>"
            f"<td>{escape(str(row['simulated_draws_avg']))}</td>"
            f"<td>{escape(str(row['simulated_losses_avg']))}</td>"
            "</tr>"
        )

    return (
        "<section class='panel'>"
        "<div class='section-heading'>"
        "<span class='eyebrow'>Simulation</span>"
        "<h2>Batch scenario view</h2>"
        "<p>Expected standings from the simulation artifact, with the projected "
        "top team emphasized.</p>"
        "</div>"
        "<div class='table-shell'><table class='simulation-table'>"
        "<thead><tr>"
        "<th>Team</th><th>Expected Points</th><th>Average Rank</th>"
        "<th>P(Top)</th><th>P(Bottom)</th><th>Wins Avg</th>"
        "<th>Draws Avg</th><th>Losses Avg</th>"
        "</tr></thead><tbody>"
        + "".join(body_rows)
        + "</tbody></table></div></section>"
    )


def _render_html(data: dict[str, Any]) -> str:
    badge = data["status_badge"]
    cards_html = "".join(
        (
            f"<article class='summary-card summary-{escape(card['tone'])}'>"
            f"<div class='summary-label'>{escape(str(card['label']))}</div>"
            f"<div class='summary-value'>{escape(str(card['value']))}</div>"
            "</article>"
        )
        for card in data["summary_cards"]
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(str(data['title']))}</title>
  <style>
    :root {{
      --bg: #eef3f6;
      --panel: rgba(255, 255, 255, 0.92);
      --panel-strong: #ffffff;
      --ink: #0f1d34;
      --muted: #637289;
      --line: rgba(15, 29, 52, 0.1);
      --shadow: 0 22px 50px rgba(15, 29, 52, 0.08);
      --navy: #12335f;
      --navy-deep: #0b2342;
      --teal: #14b8a6;
      --teal-soft: #d8fbf5;
      --green: #22c55e;
      --gold: #f6c453;
      --warn: #fff3cc;
      --warn-line: #f3cf67;
      --danger: #fef0ee;
      --danger-line: #f0a49b;
      --away: #3b82f6;
      --draw: #94a3b8;
      --home: #14b8a6;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(20, 184, 166, 0.12), transparent 32%),
        radial-gradient(circle at top right, rgba(18, 51, 95, 0.12), transparent 26%),
        linear-gradient(180deg, #f8fbfc 0%, var(--bg) 100%);
    }}
    main {{
      max-width: 1240px;
      margin: 0 auto;
      padding: 32px 20px 56px;
    }}
    .hero {{
      position: relative;
      overflow: hidden;
      background:
        linear-gradient(135deg, rgba(11, 35, 66, 0.96), rgba(18, 51, 95, 0.92)),
        linear-gradient(180deg, #12335f 0%, #0b2342 100%);
      color: #f8fbff;
      border-radius: 28px;
      padding: 34px 34px 28px;
      box-shadow: 0 28px 60px rgba(10, 22, 41, 0.28);
      margin-bottom: 24px;
    }}
    .hero::before {{
      content: "";
      position: absolute;
      inset: 0;
      background:
        radial-gradient(circle at 18% 18%, rgba(20, 184, 166, 0.38), transparent 18%),
        radial-gradient(circle at 80% 28%, rgba(255, 255, 255, 0.14), transparent 16%),
        linear-gradient(120deg, transparent 0%, rgba(255, 255, 255, 0.04) 100%);
      pointer-events: none;
    }}
    .hero-grid {{
      position: relative;
      display: grid;
      grid-template-columns: minmax(0, 2fr) minmax(260px, 1fr);
      gap: 24px;
      align-items: start;
    }}
    .hero-kicker {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.08);
      color: #ccecf1;
      font-size: 0.85rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    .hero h1 {{
      font-size: clamp(2.2rem, 5vw, 4.2rem);
      line-height: 0.96;
      margin: 16px 0 10px;
      letter-spacing: -0.04em;
    }}
    .hero-subtitle {{
      max-width: 58ch;
      color: #d8e6f7;
      font-size: 1.02rem;
      line-height: 1.65;
      margin: 0;
    }}
    .hero-meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 18px;
    }}
    .meta-pill {{
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 999px;
      padding: 10px 14px;
      font-size: 0.92rem;
      color: #ecf5ff;
    }}
    .hero-side {{
      position: relative;
      z-index: 1;
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 22px;
      padding: 18px;
      backdrop-filter: blur(10px);
    }}
    .status-badge {{
      display: inline-flex;
      align-items: center;
      padding: 8px 12px;
      border-radius: 999px;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      font-size: 0.78rem;
    }}
    .status-official {{ background: rgba(34, 197, 94, 0.18); color: #d8ffe6; }}
    .status-draft {{ background: rgba(246, 196, 83, 0.2); color: #fff1c5; }}
    .status-demo {{ background: rgba(20, 184, 166, 0.18); color: #d2fff7; }}
    .hero-side h2 {{
      margin: 14px 0 10px;
      font-size: 1.05rem;
      color: #ffffff;
    }}
    .hero-side p {{
      margin: 0;
      color: #d9e8fb;
      line-height: 1.6;
      font-size: 0.94rem;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 24px;
      padding: 24px;
      box-shadow: var(--shadow);
      margin-bottom: 22px;
      backdrop-filter: blur(6px);
    }}
    .section-heading {{
      margin-bottom: 18px;
    }}
    .eyebrow {{
      display: inline-block;
      margin-bottom: 8px;
      color: var(--teal);
      font-size: 0.78rem;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    .section-heading h2 {{
      margin: 0 0 8px;
      font-size: 1.55rem;
      letter-spacing: -0.03em;
    }}
    .section-heading p,
    .empty {{
      margin: 0;
      color: var(--muted);
      line-height: 1.65;
    }}
    .summary-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 14px;
    }}
    .summary-card {{
      border-radius: 20px;
      padding: 18px 18px 20px;
      color: #ffffff;
      box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.12);
    }}
    .summary-navy {{
      background: linear-gradient(135deg, #0b2342, #12335f);
    }}
    .summary-teal {{
      background: linear-gradient(135deg, #0d6f74, #14b8a6);
    }}
    .summary-green {{
      background: linear-gradient(135deg, #17784b, #22c55e);
    }}
    .summary-gold {{
      background: linear-gradient(135deg, #aa7c13, #f6c453);
      color: #3b2a02;
    }}
    .summary-label {{
      font-size: 0.88rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      opacity: 0.92;
    }}
    .summary-value {{
      margin-top: 10px;
      font-size: 2.15rem;
      font-weight: 800;
      letter-spacing: -0.04em;
    }}
    .prediction-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 18px;
    }}
    .prediction-card {{
      background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), #f8fcfd);
      border: 1px solid rgba(18, 51, 95, 0.08);
      border-radius: 24px;
      padding: 20px;
      box-shadow: 0 18px 36px rgba(18, 51, 95, 0.08);
    }}
    .prediction-top,
    .prediction-footer,
    .prob-row {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }}
    .prediction-top {{
      margin-bottom: 16px;
      align-items: flex-start;
    }}
    .prediction-meta,
    .prediction-date {{
      color: var(--muted);
      font-size: 0.86rem;
    }}
    .prediction-card h3 {{
      margin: 4px 0 0;
      font-size: 1.16rem;
    }}
    .matchup {{
      display: grid;
      grid-template-columns: 1fr auto 1fr;
      align-items: center;
      gap: 14px;
      margin-bottom: 16px;
    }}
    .team {{
      padding: 16px;
      border-radius: 18px;
      font-size: 1.16rem;
      font-weight: 700;
      line-height: 1.25;
    }}
    .team-a {{
      background: linear-gradient(
        135deg,
        rgba(20, 184, 166, 0.14),
        rgba(20, 184, 166, 0.04)
      );
      border: 1px solid rgba(20, 184, 166, 0.16);
    }}
    .team-b {{
      background: linear-gradient(
        135deg,
        rgba(59, 130, 246, 0.12),
        rgba(59, 130, 246, 0.04)
      );
      border: 1px solid rgba(59, 130, 246, 0.15);
      text-align: right;
    }}
    .versus {{
      width: 46px;
      height: 46px;
      border-radius: 50%;
      display: grid;
      place-items: center;
      background: linear-gradient(180deg, #12335f, #0b2342);
      color: #ffffff;
      font-weight: 800;
      letter-spacing: 0.04em;
      font-size: 0.78rem;
      box-shadow: 0 10px 24px rgba(18, 51, 95, 0.16);
    }}
    .prediction-highlight {{
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      gap: 10px;
      padding: 14px 16px;
      border-radius: 18px;
      background: linear-gradient(
        180deg,
        rgba(18, 51, 95, 0.05),
        rgba(20, 184, 166, 0.08)
      );
      margin-bottom: 16px;
    }}
    .outcome {{
      font-weight: 700;
      color: var(--navy);
    }}
    .score-pill {{
      background: var(--panel-strong);
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 8px 12px;
      font-weight: 600;
      color: var(--muted);
    }}
    .section-mini-title {{
      margin-bottom: 12px;
      color: var(--muted);
      font-size: 0.82rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-weight: 700;
    }}
    .probability-bars {{
      padding: 14px 0 2px;
    }}
    .prob-row {{
      margin-bottom: 12px;
      align-items: center;
    }}
    .prob-label,
    .prob-value {{
      font-size: 0.94rem;
      color: var(--muted);
      min-width: 104px;
      font-weight: 600;
    }}
    .prob-label {{
      display: flex;
      align-items: center;
      gap: 8px;
      min-width: 132px;
    }}
    .prob-label.is-top,
    .prob-value.is-top {{
      color: var(--navy);
      font-weight: 800;
    }}
    .prob-code {{
      width: 28px;
      height: 28px;
      border-radius: 999px;
      display: grid;
      place-items: center;
      background: #edf2f7;
      color: var(--navy);
      font-weight: 800;
      font-size: 0.84rem;
    }}
    .prob-track {{
      flex: 1;
      min-width: 0;
      height: 12px;
      border-radius: 999px;
      background: #e4ebf2;
      overflow: hidden;
    }}
    .prob-fill {{
      height: 100%;
      border-radius: 999px;
    }}
    .prob-home {{
      background: linear-gradient(90deg, #0d9488, var(--home));
    }}
    .prob-draw {{
      background: linear-gradient(90deg, #94a3b8, var(--draw));
    }}
    .prob-away {{
      background: linear-gradient(90deg, #2563eb, var(--away));
    }}
    .prob-fill.is-top {{
      box-shadow: 0 0 0 3px rgba(20, 184, 166, 0.12);
    }}
    .model-chip,
    .micro-badge,
    .table-badge {{
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 7px 11px;
      font-size: 0.78rem;
      font-weight: 700;
      letter-spacing: 0.02em;
    }}
    .model-chip {{
      background: #edf4ff;
      color: var(--navy);
      border: 1px solid rgba(18, 51, 95, 0.12);
    }}
    .badge-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      justify-content: flex-end;
    }}
    .official {{
      background: rgba(34, 197, 94, 0.14);
      color: #18734a;
    }}
    .frozen {{
      background: rgba(59, 130, 246, 0.13);
      color: #1e56c8;
    }}
    .confidence {{
      background: rgba(20, 184, 166, 0.14);
      color: #0f766e;
      text-transform: uppercase;
    }}
    .table-shell {{
      overflow-x: auto;
      border-radius: 18px;
      border: 1px solid var(--line);
      background: #fbfdff;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.94rem;
    }}
    th, td {{
      padding: 14px 16px;
      text-align: left;
      border-bottom: 1px solid rgba(15, 29, 52, 0.08);
      white-space: nowrap;
    }}
    th {{
      background: rgba(18, 51, 95, 0.04);
      color: var(--navy);
      font-size: 0.84rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }}
    .top-team-row {{
      background: rgba(20, 184, 166, 0.06);
    }}
    .team-cell {{
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 700;
      color: var(--navy);
    }}
    .top-badge {{
      background: rgba(20, 184, 166, 0.16);
      color: #0f766e;
    }}
    .teal-badge {{
      background: rgba(20, 184, 166, 0.14);
      color: #0f766e;
    }}
    .amber-badge {{
      background: rgba(246, 196, 83, 0.2);
      color: #956b00;
    }}
    .artifact-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 14px;
    }}
    .artifact-card {{
      background: linear-gradient(180deg, #ffffff, #f8fbfd);
      border: 1px solid var(--line);
      border-radius: 20px;
      padding: 18px;
      box-shadow: 0 14px 30px rgba(18, 51, 95, 0.06);
    }}
    .artifact-top {{
      display: flex;
      justify-content: flex-end;
      margin-bottom: 10px;
    }}
    .artifact-status {{
      display: inline-flex;
      align-items: center;
      padding: 6px 10px;
      border-radius: 999px;
      font-size: 0.74rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }}
    .artifact-ready {{
      background: rgba(20, 184, 166, 0.14);
      color: #0f766e;
    }}
    .artifact-missing {{
      background: rgba(239, 68, 68, 0.12);
      color: #b42318;
    }}
    .artifact-card h3 {{
      margin: 0 0 10px;
      font-size: 1.02rem;
    }}
    .artifact-card p {{
      margin: 0;
      color: var(--muted);
      line-height: 1.6;
    }}
    code {{
      display: inline-block;
      max-width: 100%;
      overflow-wrap: anywhere;
      font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace;
      font-size: 0.86rem;
      background: rgba(18, 51, 95, 0.04);
      padding: 4px 6px;
      border-radius: 8px;
    }}
    .warnings-panel {{
      border-left: 6px solid #d5dee8;
    }}
    .warnings-panel.has-warnings {{
      background: linear-gradient(180deg, var(--warn), #fffdf5);
      border-left-color: var(--warn-line);
    }}
    .warning-list {{
      margin: 0;
      padding-left: 20px;
      color: #7a5803;
    }}
    footer {{
      text-align: center;
      color: var(--muted);
      font-size: 0.92rem;
      padding: 10px 0 0;
    }}
    @media (max-width: 840px) {{
      .hero-grid {{
        grid-template-columns: 1fr;
      }}
      .matchup {{
        grid-template-columns: 1fr;
      }}
      .team-b {{
        text-align: left;
      }}
      .versus {{
        margin: 0 auto;
      }}
      .prediction-footer,
      .prob-row {{
        flex-direction: column;
        align-items: flex-start;
      }}
      .prob-track {{
        width: 100%;
      }}
      .badge-row {{
        justify-content: flex-start;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <div class="hero-grid">
        <div>
          <div class="hero-kicker">Hackathon Demo Dashboard</div>
          <h1>{escape(str(data['title']))}</h1>
          <p class="hero-subtitle">
            Static World Cup batch viewer built from generated artifacts. A polished
            tournament-facing snapshot of predictions, simulation context, and
            export outputs.
          </p>
          <div class="hero-meta">
            <span class="meta-pill">Batch: {escape(str(data['batch_code']))}</span>
            <span class="meta-pill">
              Generated: {escape(str(data['generated_at']))}
            </span>
          </div>
        </div>
        <aside class="hero-side">
          <span class="status-badge status-{escape(badge['tone'])}">
            {escape(badge['label'])}
          </span>
          <h2>Dashboard demo status</h2>
          <p>
            This static viewer is optimized for final demo walkthroughs:
            modern, offline, and generated directly from existing project
            artifacts.
          </p>
        </aside>
      </div>
    </section>
    <section class="panel">
      <div class="section-heading">
        <span class="eyebrow">Summary</span>
        <h2>Batch snapshot</h2>
        <p>Key metrics for the current World Cup prediction batch.</p>
      </div>
      <div class="summary-grid">{cards_html}</div>
    </section>
    {_predictions_html(data["prediction_cards"])}
    {_simulation_html(data["simulation_table"])}
    {_artifacts_html(data["artifact_links"])}
    {_warnings_html(data["warnings"])}
    <footer>Generated artifact. PostgreSQL remains source of truth.</footer>
  </main>
</body>
</html>
"""


def build_static_dashboard(
    *,
    batch_code: str,
    output_dir: Path | str = DEFAULT_OUTPUT_ROOT,
    include_simulation: bool = False,
    title: str = "World Cup 2026 Predictor",
) -> dict[str, Any]:
    paths = _artifact_paths(batch_code)
    batch_report = _read_json(paths["batch_report_json"])
    predictions_rows = _read_csv(paths["predictions_csv"])
    simulation_rows: list[dict[str, str]] = []

    if include_simulation:
        simulation_path = paths["simulation_csv"]
        if simulation_path.is_file():
            simulation_rows = _read_csv(simulation_path)

    warnings = list(batch_report.get("warnings") or [])
    if include_simulation and not paths["simulation_csv"].is_file():
        warnings.append(
            "simulation_results.csv was requested but is not available for this batch"
        )

    artifact_links = [
        _link_item("Batch report HTML", paths["batch_report_html"], required=False),
        _link_item("Predictions CSV", paths["predictions_csv"], required=True),
        _link_item("Simulation results CSV", paths["simulation_csv"], required=False),
    ]
    summary = batch_report.get("summary") or {}
    data = {
        "title": title,
        "batch_code": batch_report.get("batch_code", batch_code),
        "generated_at": batch_report.get("generated_at", "unknown"),
        "summary": summary,
        "summary_cards": _summary_cards(batch_report),
        "status_badge": _result_badge(summary),
        "predictions_rows": predictions_rows,
        "prediction_cards": _prediction_cards(predictions_rows),
        "simulation_rows": simulation_rows,
        "simulation_table": _simulation_table(simulation_rows),
        "artifact_links": artifact_links,
        "warnings": warnings,
    }

    output_root = Path(output_dir) / batch_code
    output_root.mkdir(parents=True, exist_ok=True)
    data_path = output_root / "dashboard_data.json"
    html_path = output_root / "index.html"
    data_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    html_path.write_text(_render_html(data), encoding="utf-8")
    return {
        "batch_code": batch_code,
        "output_dir": str(output_root),
        "dashboard_json": str(data_path),
        "dashboard_html": str(html_path),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a static dashboard for one batch"
    )
    parser.add_argument("--batch-code", required=True)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--include-simulation", action="store_true")
    parser.add_argument("--title", default="World Cup 2026 Predictor")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        report = build_static_dashboard(
            batch_code=args.batch_code,
            output_dir=Path(args.output_dir),
            include_simulation=args.include_simulation,
            title=args.title,
        )
    except DashboardBuildError as exc:
        raise SystemExit(f"ERROR: {exc}") from exc

    print(f"batch_code={report['batch_code']}")
    print(f"dashboard_html={report['dashboard_html']}")
    print(f"dashboard_json={report['dashboard_json']}")


if __name__ == "__main__":
    main()

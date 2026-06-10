"""Monte Carlo simulation MVP for one prediction batch."""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.connection import get_session
from src.db.models import (
    Batch,
    BatchMatch,
    Match,
    Prediction,
    SimulationRun,
    Team,
)

REPORTS_ROOT = Path("data/processed/simulation_reports")


def normalize_probability_triplet(
    p_team_a_win_90: float,
    p_draw_90: float,
    p_team_b_win_90: float,
) -> tuple[float, float, float]:
    values = [
        max(0.0, float(p_team_a_win_90)),
        max(0.0, float(p_draw_90)),
        max(0.0, float(p_team_b_win_90)),
    ]
    total = sum(values)
    if total <= 0:
        uniform = 1.0 / 3.0
        return uniform, uniform, uniform
    return values[0] / total, values[1] / total, values[2] / total


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
            prediction
            for prediction in ordered
            if prediction.is_official or prediction.is_frozen
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
        warnings.append("only draft predictions were available for simulation")
    return selected, warnings


def _simulate_outcome(
    rng: random.Random,
    prediction: Prediction,
) -> str:
    p_a, p_draw, p_b = normalize_probability_triplet(
        prediction.p_team_a_win_90,
        prediction.p_draw_90,
        prediction.p_team_b_win_90,
    )
    roll = rng.random()
    if roll < p_a:
        return "team_a_win"
    if roll < p_a + p_draw:
        return "draw"
    return "team_b_win"


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "team_id",
        "team_name",
        "expected_points",
        "average_rank",
        "probability_top_batch",
        "probability_bottom_batch",
        "simulated_wins_total",
        "simulated_draws_total",
        "simulated_losses_total",
        "simulated_wins_avg",
        "simulated_draws_avg",
        "simulated_losses_avg",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_markdown(path: Path, report: dict[str, Any]) -> None:
    lines = [
        f"# Simulation Report: {report['batch_code']}",
        "",
        f"- Runs: {report['runs']}",
        f"- Generated at: `{report['generated_at']}`",
        f"- Official only: `{report['official_only']}`",
        f"- Include drafts: `{report['include_drafts']}`",
        "",
        "## Summary",
        f"- Matches in batch: {report['summary']['matches_in_batch']}",
        f"- Matches simulated: {report['summary']['matches_simulated']}",
        f"- Teams simulated: {report['summary']['teams_simulated']}",
        "",
        "## Team Results",
        "",
        (
            "| Team | Expected Points | Average Rank | P(Top) | P(Bottom) | "
            "Wins Avg | Draws Avg | Losses Avg |"
        ),
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in report["team_results"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["team_name"]),
                    str(row["expected_points"]),
                    str(row["average_rank"]),
                    str(row["probability_top_batch"]),
                    str(row["probability_bottom_batch"]),
                    str(row["simulated_wins_avg"]),
                    str(row["simulated_draws_avg"]),
                    str(row["simulated_losses_avg"]),
                ]
            )
            + " |"
        )
    lines.extend(["", "## Warnings"])
    if report["warnings"]:
        lines.extend(f"- {warning}" for warning in report["warnings"])
    else:
        lines.append("- None.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_json(path: Path, report: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(report, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )


def simulate_batch(
    session: Session,
    *,
    batch_code: str,
    runs: int = 10000,
    official_only: bool = False,
    include_drafts: bool = False,
    seed: int = 42,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    batch = session.scalar(select(Batch).where(Batch.code == batch_code))
    if batch is None:
        raise ValueError(f"unknown batch code: {batch_code}")
    if runs <= 0:
        raise ValueError("runs must be positive")

    batch_matches = session.scalars(
        select(BatchMatch)
        .where(BatchMatch.batch_id == batch.id)
        .order_by(BatchMatch.order_in_batch)
    ).all()
    match_ids = [item.match_id for item in batch_matches]
    matches = (
        session.scalars(select(Match).where(Match.id.in_(match_ids))).all()
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
    predictions_by_match: dict[int, list[Prediction]] = defaultdict(list)
    for prediction in predictions:
        predictions_by_match[prediction.match_id].append(prediction)

    selected_predictions, warnings = _select_predictions_for_matches(
        predictions_by_match,
        official_only=official_only,
        include_drafts=include_drafts,
    )

    simulation_matches: list[tuple[Match, Prediction]] = []
    for match in ordered_matches:
        prediction = selected_predictions.get(match.id)
        if prediction is None:
            warnings.append(
                f"match_id={match.id} skipped because no eligible prediction was found"
            )
            continue
        simulation_matches.append((match, prediction))

    team_ids = {
        team_id
        for match, _prediction in simulation_matches
        for team_id in (match.team_a_id, match.team_b_id)
    }
    teams = {
        team.id: team
        for team in session.scalars(
            select(Team).where(Team.id.in_(sorted(team_ids)))
        ).all()
    }

    metrics: dict[int, dict[str, float]] = {
        team_id: {
            "points_total": 0.0,
            "rank_total": 0.0,
            "top_count": 0.0,
            "bottom_count": 0.0,
            "wins_total": 0.0,
            "draws_total": 0.0,
            "losses_total": 0.0,
        }
        for team_id in team_ids
    }

    rng = random.Random(seed)
    for _ in range(runs):
        simulation_points = {team_id: 0 for team_id in team_ids}
        simulation_wins = {team_id: 0 for team_id in team_ids}
        simulation_draws = {team_id: 0 for team_id in team_ids}
        simulation_losses = {team_id: 0 for team_id in team_ids}

        for match, prediction in simulation_matches:
            outcome = _simulate_outcome(rng, prediction)
            if outcome == "team_a_win":
                simulation_points[match.team_a_id] += 3
                simulation_wins[match.team_a_id] += 1
                simulation_losses[match.team_b_id] += 1
            elif outcome == "team_b_win":
                simulation_points[match.team_b_id] += 3
                simulation_wins[match.team_b_id] += 1
                simulation_losses[match.team_a_id] += 1
            else:
                simulation_points[match.team_a_id] += 1
                simulation_points[match.team_b_id] += 1
                simulation_draws[match.team_a_id] += 1
                simulation_draws[match.team_b_id] += 1

        ordered_team_ids = sorted(
            team_ids,
            key=lambda team_id: (-simulation_points[team_id], team_id),
        )
        rank_by_team = {
            team_id: rank
            for rank, team_id in enumerate(ordered_team_ids, start=1)
        }
        if ordered_team_ids:
            top_team_id = ordered_team_ids[0]
            bottom_team_id = ordered_team_ids[-1]
            metrics[top_team_id]["top_count"] += 1
            metrics[bottom_team_id]["bottom_count"] += 1

        for team_id in team_ids:
            metrics[team_id]["points_total"] += simulation_points[team_id]
            metrics[team_id]["rank_total"] += rank_by_team[team_id]
            metrics[team_id]["wins_total"] += simulation_wins[team_id]
            metrics[team_id]["draws_total"] += simulation_draws[team_id]
            metrics[team_id]["losses_total"] += simulation_losses[team_id]

    team_results: list[dict[str, Any]] = []
    for team_id in sorted(team_ids):
        team = teams.get(team_id)
        team_name = team.name if team is not None else f"team_{team_id}"
        stat = metrics[team_id]
        team_results.append(
            {
                "team_id": team_id,
                "team_name": team_name,
                "expected_points": stat["points_total"] / runs,
                "average_rank": stat["rank_total"] / runs,
                "probability_top_batch": stat["top_count"] / runs,
                "probability_bottom_batch": stat["bottom_count"] / runs,
                "simulated_wins_total": int(stat["wins_total"]),
                "simulated_draws_total": int(stat["draws_total"]),
                "simulated_losses_total": int(stat["losses_total"]),
                "simulated_wins_avg": stat["wins_total"] / runs,
                "simulated_draws_avg": stat["draws_total"] / runs,
                "simulated_losses_avg": stat["losses_total"] / runs,
            }
        )

    model_run_ids = {
        prediction.model_run_id
        for _match, prediction in simulation_matches
        if prediction.model_run_id is not None
    }
    feature_set_ids = {
        prediction.feature_set_id
        for _match, prediction in simulation_matches
        if prediction.feature_set_id is not None
    }
    chosen_model_run_id = max(model_run_ids) if model_run_ids else None
    chosen_feature_set_id = max(feature_set_ids) if feature_set_ids else None

    simulation_run = SimulationRun(
        batch_id=batch.id,
        model_run_id=chosen_model_run_id,
        feature_set_id=chosen_feature_set_id,
        simulated_at=datetime.now(UTC),
        num_simulations=runs,
        config_json={
            "official_only": official_only,
            "include_drafts": include_drafts,
            "warnings": warnings,
            "matches_simulated": len(simulation_matches),
        },
        random_seed=seed,
    )
    session.add(simulation_run)
    session.commit()

    report = {
        "batch_code": batch.code,
        "simulation_run_id": simulation_run.id,
        "runs": runs,
        "seed": seed,
        "official_only": official_only,
        "include_drafts": include_drafts,
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "matches_in_batch": len(ordered_matches),
            "matches_simulated": len(simulation_matches),
            "teams_simulated": len(team_results),
        },
        "team_results": team_results,
        "warnings": warnings,
    }

    output_root = output_dir or REPORTS_ROOT
    batch_dir = output_root / batch.code
    batch_dir.mkdir(parents=True, exist_ok=True)
    _write_json(batch_dir / "simulation_report.json", report)
    _write_markdown(batch_dir / "simulation_report.md", report)
    _write_csv(batch_dir / "simulation_results.csv", team_results)
    report["output_dir"] = str(batch_dir)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Monte Carlo simulation for one batch"
    )
    parser.add_argument("--batch-code", required=True)
    parser.add_argument("--runs", type=int, default=10000)
    parser.add_argument("--official-only", action="store_true")
    parser.add_argument("--include-drafts", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=Path, default=REPORTS_ROOT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with get_session() as session:
        report = simulate_batch(
            session,
            batch_code=args.batch_code,
            runs=args.runs,
            official_only=args.official_only,
            include_drafts=args.include_drafts,
            seed=args.seed,
            output_dir=args.output_dir,
        )
    print(f"simulation_run_id={report['simulation_run_id']}")
    print(f"output_dir={report['output_dir']}")


if __name__ == "__main__":
    main()

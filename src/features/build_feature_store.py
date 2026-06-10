"""Build a reproducible feature store for one batch."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, time, timedelta
from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.connection import get_session
from src.db.models import Batch, BatchMatch, FeatureSet, Match, MatchFeature

CONFIG_PATH = Path("config/feature_config.yaml")
REPORTS_ROOT = Path("data/processed/feature_reports")
FEATURE_NAMES = [
    "team_a_id",
    "team_b_id",
    "stage",
    "is_knockout",
    "neutral_site",
    "team_a_goals_for_recent",
    "team_b_goals_for_recent",
    "team_a_goals_against_recent",
    "team_b_goals_against_recent",
    "goals_for_recent_diff",
    "goals_against_recent_diff",
    "recent_form_points_diff",
]


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _match_datetime(match: Match) -> datetime | None:
    if match.date is None:
        return None
    kickoff_time = match.kickoff_time or time.min
    return datetime.combine(match.date, kickoff_time, tzinfo=UTC)


def _is_before_or_at_cutoff(match: Match, cutoff_time: datetime) -> bool:
    if match.date is None:
        return False
    normalized_cutoff = _ensure_utc(cutoff_time)
    if match.date < normalized_cutoff.date():
        return True
    if match.date > normalized_cutoff.date():
        return False
    if match.kickoff_time is None:
        return False
    match_dt = datetime.combine(match.date, match.kickoff_time, tzinfo=UTC)
    return match_dt <= normalized_cutoff


def _is_before_reference(match: Match, reference_time: datetime) -> bool:
    match_dt = _match_datetime(match)
    if match_dt is None:
        return False
    return match_dt < _ensure_utc(reference_time)


def _result_for_team(match: Match, team_id: int) -> tuple[int, int, int]:
    if match.team_a_goals is None or match.team_b_goals is None:
        return 0, 0, 0

    if team_id == match.team_a_id:
        goals_for = match.team_a_goals
        goals_against = match.team_b_goals
    else:
        goals_for = match.team_b_goals
        goals_against = match.team_a_goals

    if goals_for > goals_against:
        points = 3
    elif goals_for == goals_against:
        points = 1
    else:
        points = 0

    return goals_for, goals_against, points


def _target_result(match: Match) -> str | None:
    if match.team_a_goals is None or match.team_b_goals is None:
        return None
    if match.team_a_goals > match.team_b_goals:
        return "team_a_win"
    if match.team_a_goals < match.team_b_goals:
        return "team_b_win"
    return "draw"


def _is_knockout(stage: str | None) -> bool:
    if not stage:
        return False
    return "group" not in stage.casefold()


def load_feature_config(config_path: Path | None = None) -> dict:
    path = config_path or CONFIG_PATH
    content = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    features = content.get("features") or {}
    return {
        "version": features.get("version", "v1"),
        "recent_form_window_matches": int(
            features.get("recent_form_window_matches", 5)
        ),
        "recent_form_window_days": int(features.get("recent_form_window_days", 365)),
    }


def _recent_team_stats(
    finished_matches: list[Match],
    team_id: int,
    cutoff_time: datetime,
    reference_time: datetime,
    config: dict,
) -> dict[str, int]:
    earliest_time = _ensure_utc(reference_time) - timedelta(
        days=int(config["recent_form_window_days"])
    )
    relevant_matches: list[Match] = []
    for match in finished_matches:
        if team_id not in {match.team_a_id, match.team_b_id}:
            continue
        if not _is_before_or_at_cutoff(match, cutoff_time):
            continue
        if not _is_before_reference(match, reference_time):
            continue
        match_dt = _match_datetime(match)
        if match_dt is None or match_dt < earliest_time:
            continue
        relevant_matches.append(match)

    relevant_matches.sort(
        key=lambda item: _match_datetime(item) or datetime.min.replace(tzinfo=UTC)
    )
    recent_matches = relevant_matches[-int(config["recent_form_window_matches"]) :]

    goals_for = 0
    goals_against = 0
    recent_form_points = 0
    for match in recent_matches:
        match_goals_for, match_goals_against, match_points = _result_for_team(
            match, team_id
        )
        goals_for += match_goals_for
        goals_against += match_goals_against
        recent_form_points += match_points

    return {
        "goals_for_recent": goals_for,
        "goals_against_recent": goals_against,
        "recent_form_points": recent_form_points,
    }


def _features_for_match(
    match: Match,
    finished_matches: list[Match],
    cutoff_time: datetime,
    config: dict,
    reference_time: datetime,
) -> dict:
    team_a_stats = _recent_team_stats(
        finished_matches, match.team_a_id, cutoff_time, reference_time, config
    )
    team_b_stats = _recent_team_stats(
        finished_matches, match.team_b_id, cutoff_time, reference_time, config
    )
    return {
        "team_a_id": match.team_a_id,
        "team_b_id": match.team_b_id,
        "stage": match.stage,
        "is_knockout": _is_knockout(match.stage),
        "neutral_site": bool(match.neutral_site),
        "team_a_goals_for_recent": team_a_stats["goals_for_recent"],
        "team_b_goals_for_recent": team_b_stats["goals_for_recent"],
        "team_a_goals_against_recent": team_a_stats["goals_against_recent"],
        "team_b_goals_against_recent": team_b_stats["goals_against_recent"],
        "goals_for_recent_diff": (
            team_a_stats["goals_for_recent"] - team_b_stats["goals_for_recent"]
        ),
        "goals_against_recent_diff": (
            team_a_stats["goals_against_recent"] - team_b_stats["goals_against_recent"]
        ),
        "recent_form_points_diff": (
            team_a_stats["recent_form_points"] - team_b_stats["recent_form_points"]
        ),
    }


def _load_batch_matches(session: Session, batch_id: int) -> list[Match]:
    return (
        session.query(Match)
        .join(BatchMatch, BatchMatch.match_id == Match.id)
        .filter(BatchMatch.batch_id == batch_id)
        .order_by(Match.date, Match.kickoff_time, Match.id)
        .all()
    )


def _ensure_batch_cutoff(
    session: Session,
    batch: Batch,
    scheduled_matches: list[Match],
    warnings: list[str],
) -> datetime:
    if batch.cutoff_time is not None:
        return _ensure_utc(batch.cutoff_time)

    first_match_start = next(
        (
            match_dt
            for match_dt in (_match_datetime(match) for match in scheduled_matches)
            if match_dt is not None
        ),
        None,
    )
    if first_match_start is None:
        raise ValueError("batch has no scheduled matches with a usable datetime")

    batch.first_match_start = first_match_start
    batch.cutoff_time = first_match_start - timedelta(minutes=10)
    session.flush()
    warnings.append(
        "batch cutoff_time was missing and has been inferred from the "
        "first scheduled match"
    )
    return _ensure_utc(batch.cutoff_time)


def _write_feature_report(report_root: Path, feature_set_id: int, report: dict) -> Path:
    report_dir = report_root / str(feature_set_id)
    report_dir.mkdir(parents=True, exist_ok=True)

    json_path = report_dir / "feature_report.json"
    json_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )

    markdown_path = report_dir / "feature_report.md"
    lines = [
        "# Feature Report",
        "",
        f"- Feature set id: {feature_set_id}",
        f"- Batch code: `{report['batch_code']}`",
        f"- Cutoff time: `{report['cutoff_time']}`",
        f"- Training rows: {report['training_rows']}",
        f"- Prediction rows: {report['prediction_rows']}",
        f"- Leakage check passed: `{report['leakage_check_passed']}`",
        "",
        "## Features",
    ]
    lines.extend(f"- `{feature_name}`" for feature_name in report["features"])
    lines.extend(["", "## Warnings"])
    if report["warnings"]:
        lines.extend(f"- {warning}" for warning in report["warnings"])
    else:
        lines.append("- None.")
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return report_dir


def build_feature_store(
    session: Session,
    batch_code: str,
    config_path: Path | None = None,
    report_root: Path | None = None,
) -> dict:
    batch = session.scalar(
        select(Batch).where(Batch.code == batch_code).order_by(Batch.id)
    )
    if batch is None:
        raise ValueError(f"unknown batch code: {batch_code}")

    config = load_feature_config(config_path)
    warnings: list[str] = []
    report_root = report_root or REPORTS_ROOT

    batch_matches = _load_batch_matches(session, batch.id)
    scheduled_matches = [
        match for match in batch_matches if match.status == "scheduled"
    ]
    if not scheduled_matches:
        raise ValueError("batch has no scheduled matches to build prediction rows")

    cutoff_time = _ensure_batch_cutoff(session, batch, scheduled_matches, warnings)

    finished_matches = [
        match
        for match in session.scalars(
            select(Match).where(
                Match.status == "finished",
                Match.team_a_goals.is_not(None),
                Match.team_b_goals.is_not(None),
            )
        ).all()
        if _is_before_or_at_cutoff(match, cutoff_time)
    ]

    feature_set = FeatureSet(
        name=f"feature_store_{batch.code}",
        version=config["version"],
        batch_id=batch.id,
        cutoff_time=cutoff_time,
        feature_config_json={
            "feature_names": FEATURE_NAMES,
            "recent_form_window_matches": config["recent_form_window_matches"],
            "recent_form_window_days": config["recent_form_window_days"],
        },
        rows_count=0,
        data_coverage_json=None,
    )
    session.add(feature_set)
    session.flush()

    training_rows = 0
    prediction_rows = 0
    leakage_check_passed = True

    for match in sorted(
        finished_matches,
        key=lambda item: _match_datetime(item) or datetime.min.replace(tzinfo=UTC),
    ):
        reference_time = _match_datetime(match)
        if reference_time is None:
            continue
        session.add(
            MatchFeature(
                feature_set_id=feature_set.id,
                match_id=match.id,
                team_a_id=match.team_a_id,
                team_b_id=match.team_b_id,
                features_json=_features_for_match(
                    match,
                    finished_matches,
                    cutoff_time,
                    config,
                    reference_time,
                ),
                target_result=_target_result(match),
            )
        )
        training_rows += 1

    for match in scheduled_matches:
        session.add(
            MatchFeature(
                feature_set_id=feature_set.id,
                match_id=match.id,
                team_a_id=match.team_a_id,
                team_b_id=match.team_b_id,
                features_json=_features_for_match(
                    match,
                    finished_matches,
                    cutoff_time,
                    config,
                    cutoff_time,
                ),
                target_result=None,
            )
        )
        prediction_rows += 1

    for source_match in finished_matches:
        if not _is_before_or_at_cutoff(source_match, cutoff_time):
            leakage_check_passed = False
            break

    feature_set.rows_count = training_rows + prediction_rows
    feature_set.data_coverage_json = {
        "training_rows": training_rows,
        "prediction_rows": prediction_rows,
        "leakage_check_passed": leakage_check_passed,
        "recent_form_window_matches": config["recent_form_window_matches"],
        "recent_form_window_days": config["recent_form_window_days"],
        "warnings": warnings,
    }
    session.flush()

    report = {
        "feature_set_id": feature_set.id,
        "batch_code": batch.code,
        "cutoff_time": cutoff_time.isoformat(),
        "training_rows": training_rows,
        "prediction_rows": prediction_rows,
        "features": FEATURE_NAMES,
        "warnings": warnings,
        "leakage_check_passed": leakage_check_passed,
    }
    report_dir = _write_feature_report(report_root, feature_set.id, report)
    session.commit()

    report["report_dir"] = str(report_dir)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build feature store rows for one batch"
    )
    parser.add_argument("--batch-code", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with get_session() as session:
        report = build_feature_store(session=session, batch_code=args.batch_code)
    print(f"feature_set_id={report['feature_set_id']}")
    print(f"report_dir={report['report_dir']}")


if __name__ == "__main__":
    main()

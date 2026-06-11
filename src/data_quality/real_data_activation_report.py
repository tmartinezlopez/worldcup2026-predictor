"""Build a real-data activation report from PostgreSQL and recent artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.db.connection import get_session
from src.db.models import Competition, Match, Team, TeamAlias

DEFAULT_OUTPUT_DIR = Path("data/processed/real_data_reports")
STAGING_IMPORTS_ROOT = Path("data/staging/imports")


def _latest_file(pattern: str) -> Path | None:
    matches = sorted(STAGING_IMPORTS_ROOT.glob(pattern))
    if not matches:
        return None
    return matches[-1]


def _load_json(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _competition_summary(session: Session) -> list[dict[str, Any]]:
    rows = session.execute(
        select(
            Competition.name,
            func.count(Match.id).label("matches_count"),
        )
        .join(Match, Match.competition_id == Competition.id, isouter=True)
        .group_by(Competition.id, Competition.name)
        .order_by(func.count(Match.id).desc(), Competition.name.asc())
    ).all()
    return [
        {
            "competition": str(name),
            "matches_count": int(matches_count or 0),
        }
        for name, matches_count in rows
    ]


def _readiness_section(
    finished_matches_count: int,
    *,
    min_finished_matches: int,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if finished_matches_count < min_finished_matches:
        reasons.append(
            "finished_matches_count is below the minimum threshold for training: "
            f"{finished_matches_count} < {min_finished_matches}"
        )
    return (not reasons, reasons)


def _warning_list(
    *,
    matches_count: int,
    finished_matches_count: int,
    min_finished_matches: int,
    latest_promotion_report: dict[str, Any] | None,
    latest_source_audit_report: dict[str, Any] | None,
) -> list[str]:
    warnings: list[str] = []
    if latest_promotion_report is None:
        warnings.append("no real historical data promoted report was detected")
    if finished_matches_count < min_finished_matches:
        warnings.append(
            "too few finished matches for confident training readiness: "
            f"{finished_matches_count}"
        )
    unresolved_count = len(
        (latest_promotion_report or {}).get("unresolved_teams") or []
    )
    if unresolved_count >= 5:
        warnings.append(
            "many unresolved teams were detected in the latest promotion report: "
            f"{unresolved_count}"
        )
    if latest_source_audit_report is None and matches_count > 0:
        warnings.append(
            "only sample data detected or no real-source audit report was found"
        )
    return warnings


def _report_markdown(report: dict[str, Any]) -> str:
    competition_lines = report["competitions_top"] or []
    readiness_reasons = report["readiness"]["reasons"] or []
    warnings = report["warnings"] or []

    lines = [
        "# Real Data Activation Report",
        "",
        f"- Generated at: `{report['generated_at']}`",
        f"- Teams count: {report['teams_count']}",
        f"- Matches count: {report['matches_count']}",
        f"- Finished matches count: {report['finished_matches_count']}",
        f"- Scheduled matches count: {report['scheduled_matches_count']}",
        f"- Competitions count: {report['competitions_count']}",
        f"- Date min: {report['date_min']}",
        f"- Date max: {report['date_max']}",
        f"- Teams with aliases count: {report['teams_with_aliases_count']}",
        (
            "- Latest historical promotion report: "
            f"{report['latest_historical_promotion_report']}"
        ),
        f"- Latest source audit report: {report['latest_source_audit_report']}",
        "",
        "## Readiness",
        f"- Ready for training: `{report['readiness']['ready_for_training']}`",
        f"- Minimum finished matches threshold: {report['min_finished_matches']}",
    ]

    if readiness_reasons:
        lines.extend(f"- {reason}" for reason in readiness_reasons)
    else:
        lines.append("- No blocking readiness reasons detected.")

    lines.extend(["", "## Competitions Top"])
    if competition_lines:
        for item in competition_lines:
            lines.append(
                f"- `{item['competition']}`: {item['matches_count']} matches"
            )
    else:
        lines.append("- None.")

    lines.extend(["", "## Warnings"])
    if warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- None.")
    return "\n".join(lines) + "\n"


def build_real_data_activation_report(
    session: Session,
    *,
    output_dir: Path | None = None,
    min_finished_matches: int = 20,
) -> dict[str, Any]:
    teams_count = int(session.scalar(select(func.count()).select_from(Team)) or 0)
    matches_count = int(session.scalar(select(func.count()).select_from(Match)) or 0)
    finished_matches_count = int(
        session.scalar(
            select(func.count()).select_from(Match).where(Match.status == "finished")
        )
        or 0
    )
    scheduled_matches_count = int(
        session.scalar(
            select(func.count()).select_from(Match).where(Match.status == "scheduled")
        )
        or 0
    )
    competitions_count = int(
        session.scalar(select(func.count()).select_from(Competition)) or 0
    )
    teams_with_aliases_count = int(
        session.scalar(select(func.count(func.distinct(TeamAlias.team_id)))) or 0
    )
    date_min = session.scalar(select(func.min(Match.date)))
    date_max = session.scalar(select(func.max(Match.date)))

    latest_promotion_report_path = _latest_file(
        "historical_results_importer/*/promotion_report.json"
    )
    latest_source_audit_report_path = _latest_file(
        "*/**/source_audit_report.json"
    )
    latest_promotion_report = _load_json(latest_promotion_report_path)
    latest_source_audit_report = _load_json(latest_source_audit_report_path)

    ready_for_training, readiness_reasons = _readiness_section(
        finished_matches_count,
        min_finished_matches=min_finished_matches,
    )
    warnings = _warning_list(
        matches_count=matches_count,
        finished_matches_count=finished_matches_count,
        min_finished_matches=min_finished_matches,
        latest_promotion_report=latest_promotion_report,
        latest_source_audit_report=latest_source_audit_report,
    )

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "teams_count": teams_count,
        "matches_count": matches_count,
        "finished_matches_count": finished_matches_count,
        "scheduled_matches_count": scheduled_matches_count,
        "competitions_count": competitions_count,
        "date_min": date_min.isoformat() if date_min is not None else None,
        "date_max": date_max.isoformat() if date_max is not None else None,
        "teams_with_aliases_count": teams_with_aliases_count,
        "competitions_top": _competition_summary(session)[:10],
        "latest_historical_promotion_report": (
            str(latest_promotion_report_path) if latest_promotion_report_path else None
        ),
        "latest_source_audit_report": (
            str(latest_source_audit_report_path)
            if latest_source_audit_report_path
            else None
        ),
        "readiness": {
            "ready_for_training": ready_for_training,
            "reasons": readiness_reasons,
        },
        "warnings": warnings,
        "min_finished_matches": int(min_finished_matches),
    }

    output_dir = output_dir or DEFAULT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "real_data_activation_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "real_data_activation_report.md").write_text(
        _report_markdown(report),
        encoding="utf-8",
    )
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a real-data activation report")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--min-finished-matches", type=int, default=20)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        with get_session() as session:
            report = build_real_data_activation_report(
                session,
                output_dir=Path(args.output_dir),
                min_finished_matches=args.min_finished_matches,
            )
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"ERROR: {exc}") from exc
    print(
        "ready_for_training="
        f"{report['readiness']['ready_for_training']}"
    )
    print(f"output_dir={Path(args.output_dir)}")


if __name__ == "__main__":
    main()

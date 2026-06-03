"""Promotion report builders and writers."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path


def build_promotion_report(
    *,
    run_dir: str,
    entity_type: str,
    dry_run: bool,
    rows_read: int,
    rows_promoted: int,
    rows_skipped: int,
    teams_created: int,
    competitions_created: int,
    matches_created: int,
    matches_updated: int,
    unresolved_teams: list[dict],
    errors: list[str],
) -> dict:
    if errors:
        status = "failed"
    elif dry_run:
        status = "dry_run_passed"
    elif unresolved_teams or rows_skipped:
        status = "needs_review"
    else:
        status = "promoted"

    return {
        "run_dir": run_dir,
        "entity_type": entity_type,
        "dry_run": dry_run,
        "promoted_at": datetime.now(UTC).isoformat(),
        "rows_read": rows_read,
        "rows_promoted": rows_promoted,
        "rows_skipped": rows_skipped,
        "teams_created": teams_created,
        "competitions_created": competitions_created,
        "matches_created": matches_created,
        "matches_updated": matches_updated,
        "unresolved_teams": unresolved_teams,
        "errors": errors,
        "status": status,
    }


def write_promotion_report(run_dir: Path, report: dict) -> Path:
    path = run_dir / "promotion_report.json"
    path.write_text(
        json.dumps(report, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    return path


def write_promotion_markdown(run_dir: Path, report: dict) -> Path:
    path = run_dir / "promotion_report.md"
    lines = [
        "# Promotion Report",
        "",
        f"- Status: `{report['status']}`",
        f"- Dry run: `{report['dry_run']}`",
        f"- Rows read: {report['rows_read']}",
        f"- Rows promoted: {report['rows_promoted']}",
        f"- Rows skipped: {report['rows_skipped']}",
        f"- Teams created: {report['teams_created']}",
        f"- Competitions created: {report['competitions_created']}",
        f"- Matches created: {report['matches_created']}",
        f"- Matches updated: {report['matches_updated']}",
        "",
        "## Unresolved Teams",
    ]

    if report["unresolved_teams"]:
        for item in report["unresolved_teams"]:
            lines.append(f"- {item}")
    else:
        lines.append("- None.")

    lines.extend(["", "## Errors"])
    if report["errors"]:
        for error in report["errors"]:
            lines.append(f"- {error}")
    else:
        lines.append("- None.")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path

"""Controlled audit for the martj42 international results source."""

from __future__ import annotations

import argparse
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from urllib import error, request

from src.ingestion.importers.historical_results_importer import (
    import_historical_results,
)
from src.ingestion.source_audit import (
    SourceAuditConfig,
    build_source_audit_report,
    write_source_audit_markdown,
    write_source_audit_report,
)
from src.ingestion.source_registry import upsert_source_entry

DEFAULT_SOURCE_NAME = "martj42_international_results"
DEFAULT_SOURCE_URL = (
    "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit historical results source")
    parser.add_argument("--source-url", default=DEFAULT_SOURCE_URL)
    parser.add_argument("--local-file", type=Path)
    parser.add_argument("--max-rows", type=int)
    parser.add_argument("--source-name", default=DEFAULT_SOURCE_NAME)
    parser.add_argument("--no-download", action="store_true")
    return parser.parse_args()


def download_to_temp_file(url: str) -> Path:
    try:
        with request.urlopen(url) as response:
            with tempfile.NamedTemporaryFile(
                mode="wb", suffix=".csv", delete=False
            ) as temp_file:
                temp_file.write(response.read())
                return Path(temp_file.name)
    except (error.URLError, ValueError) as exc:
        raise RuntimeError(f"Failed to download source from {url}: {exc}") from exc


def _build_enriched_audit_report(
    config: SourceAuditConfig,
    validation_report: dict,
    normalized_records: list[dict],
    max_rows: int | None,
) -> dict:
    audit_report = build_source_audit_report(
        config,
        validation_report,
        extra_notes=[
            "Historical team names will still require identity resolution.",
            "Very old matches should not carry equal modeling weight.",
        ],
    )

    dates = sorted(
        record["date"]
        for record in normalized_records
        if record.get("date")
    )
    competitions = []
    teams = []
    for record in normalized_records:
        competition = record.get("competition")
        if competition and competition not in competitions:
            competitions.append(competition)
        for team_field in ("team_a", "team_b"):
            team = record.get(team_field)
            if team and team not in teams:
                teams.append(team)

    audit_report.update(
        {
            "source_url": config.url,
            "source_type": "historical_results",
            "audited_at": datetime.now(UTC).isoformat(),
            "partial_audit": max_rows is not None,
            "max_rows": max_rows,
            "date_min": dates[0] if dates else None,
            "date_max": dates[-1] if dates else None,
            "competitions_sample": competitions[:10],
            "teams_sample": teams[:10],
            "top_issue_values": validation_report.get("top_issue_values", {}),
        }
    )

    strengths = list(audit_report.get("strengths", []))
    strengths.extend(
        [
            "Broad historical coverage is plausible for international results.",
            "CSV format is straightforward to ingest and validate.",
            "Useful candidate for baseline training and backtesting.",
        ]
    )
    risks = list(audit_report.get("risks", []))
    risks.extend(
        [
            "License must be verified before definitive use.",
            "Old matches should be downweighted in future modeling.",
            "Team names will require identity resolution before promotion.",
            "Rows should not all receive equal modeling weight.",
        ]
    )
    audit_report["strengths"] = list(dict.fromkeys(strengths))
    audit_report["risks"] = list(dict.fromkeys(risks))
    return audit_report


def audit_historical_results_source(
    source_url: str = DEFAULT_SOURCE_URL,
    local_file: Path | None = None,
    max_rows: int | None = None,
    source_name: str = DEFAULT_SOURCE_NAME,
    no_download: bool = False,
) -> Path:
    temp_download_path: Path | None = None
    try:
        if local_file is not None:
            input_path = local_file
            metadata = {
                "local_file": str(local_file),
                "max_rows": max_rows,
            }
        else:
            if no_download:
                raise ValueError(
                    "No input source available: provide --local-file "
                    "or remove --no-download."
                )
            temp_download_path = download_to_temp_file(source_url)
            input_path = temp_download_path
            metadata = {
                "source_url": source_url,
                "downloaded_at": datetime.now(UTC).isoformat(),
                "max_rows": max_rows,
            }

        run_dir = import_historical_results(
            input_path=input_path,
            source_name=source_name,
            max_rows=max_rows,
            metadata=metadata,
        )

        normalized_records = []
        normalized_path = run_dir / "normalized.jsonl"
        with normalized_path.open("r", encoding="utf-8") as file_handle:
            for line in file_handle:
                line = line.strip()
                if line:
                    normalized_records.append(json.loads(line))

        validation_report = json.loads(
            (run_dir / "validation_report.json").read_text(encoding="utf-8")
        )
        config = SourceAuditConfig(
            source_name=source_name,
            source_type="historical_results",
            expected_format="csv",
            url=source_url,
            license="unknown_to_verify",
            local_sample_path=str(local_file) if local_file is not None else None,
            importer_name="historical_results_importer",
            notes="Controlled audit run for candidate historical results source.",
        )
        audit_report = _build_enriched_audit_report(
            config,
            validation_report,
            normalized_records,
            max_rows=max_rows,
        )
        json_path = write_source_audit_report(run_dir, audit_report)
        write_source_audit_markdown(run_dir, audit_report)

        upsert_source_entry(
            {
                "source_name": source_name,
                "source_type": "historical_results",
                "url": source_url,
                "license": "unknown_to_verify",
                "status": audit_report["status"],
                "decision": audit_report["decision"],
                "last_audited_at": audit_report["audited_at"],
                "latest_report_path": str(json_path),
                "rows_read": audit_report["rows_read"],
                "rows_valid": audit_report["rows_valid"],
                "rows_rejected": audit_report["rows_rejected"],
                "rejection_rate": audit_report["rejection_rate"],
                "date_min": audit_report.get("date_min"),
                "date_max": audit_report.get("date_max"),
                "risks": audit_report.get("risks", []),
                "notes": "Controlled historical results source audit.",
            }
        )

        return run_dir
    finally:
        if temp_download_path is not None and temp_download_path.exists():
            temp_download_path.unlink()


def main() -> None:
    args = parse_args()
    run_dir = audit_historical_results_source(
        source_url=args.source_url,
        local_file=args.local_file,
        max_rows=args.max_rows,
        source_name=args.source_name,
        no_download=args.no_download,
    )
    print(run_dir)


if __name__ == "__main__":
    main()

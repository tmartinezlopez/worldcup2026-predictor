#!/usr/bin/env bash

set -euo pipefail

source .venv/bin/activate

run_dir=$(python -m src.ingestion.importers.historical_results_importer --input data/raw/sample/historical_results_sample.csv | tail -n 1)

python - "$run_dir" <<'PY'
import json
from datetime import UTC, datetime
from pathlib import Path
import sys

from src.ingestion.source_audit import (
    SourceAuditConfig,
    build_source_audit_report,
    write_source_audit_markdown,
    write_source_audit_report,
)
from src.ingestion.source_registry import upsert_source_entry

run_dir = Path(sys.argv[1])
validation_report = json.loads((run_dir / "validation_report.json").read_text(encoding="utf-8"))

config = SourceAuditConfig(
    source_name="martj42_international_results",
    source_type="historical_results",
    url="https://github.com/martj42/international_results",
    expected_format="csv",
    license="unknown_to_verify",
    local_sample_path="data/raw/sample/historical_results_sample.csv",
    importer_name="historical_results_importer",
    notes="Sample local audit only. No remote download performed.",
)

audit_report = build_source_audit_report(
    config,
    validation_report,
    extra_notes=["Coverage and license still need manual verification."],
)
json_path = write_source_audit_report(run_dir, audit_report)
md_path = write_source_audit_markdown(run_dir, audit_report)

upsert_source_entry(
    {
        "source_name": config.source_name,
        "source_type": config.source_type,
        "url": config.url,
        "license": config.license,
        "status": audit_report["status"],
        "decision": audit_report["decision"],
        "last_audited_at": datetime.now(UTC).isoformat(),
        "notes": config.notes,
        "latest_report_path": str(json_path),
    }
)

print(f"run_dir={run_dir}")
print(f"source_audit_report_json={json_path}")
print(f"source_audit_report_md={md_path}")
print(json.dumps(audit_report, indent=2, sort_keys=True))
PY

#!/usr/bin/env bash

set -euo pipefail

source .venv/bin/activate

if ! run_dir=$(python -m src.ingestion.source_audits.historical_results_audit --source-name martj42_international_results | tail -n 1); then
  echo "Real historical-results audit failed." >&2
  echo "This flow keeps downloaded data out of versioned sample inputs and does not promote to PostgreSQL." >&2
  exit 1
fi

report_json="$run_dir/source_audit_report.json"
report_md="$run_dir/source_audit_report.md"

echo "run_dir=$run_dir"
echo "source_audit_report_json=$report_json"
echo "source_audit_report_md=$report_md"

python - "$report_json" <<'PY'
import json
from pathlib import Path
import sys

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(json.dumps({
    "source_name": report["source_name"],
    "decision": report["decision"],
    "status": report["status"],
    "rows_read": report["rows_read"],
    "rows_valid": report["rows_valid"],
    "rows_rejected": report["rows_rejected"],
    "rejection_rate": report["rejection_rate"],
    "date_min": report.get("date_min"),
    "date_max": report.get("date_max"),
    "risks": report.get("risks", []),
}, indent=2, sort_keys=True))
PY

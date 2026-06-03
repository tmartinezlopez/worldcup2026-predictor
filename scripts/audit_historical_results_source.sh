#!/usr/bin/env bash

set -euo pipefail

source .venv/bin/activate

if ! run_dir=$(python -m src.ingestion.source_audits.historical_results_audit --max-rows 5000 | tail -n 1); then
  echo "Remote audit failed. If you are offline, retry with:" >&2
  echo "python -m src.ingestion.source_audits.historical_results_audit --local-file data/raw/sample/historical_results_sample.csv --no-download --max-rows 5000" >&2
  exit 1
fi
echo "run_dir=$run_dir"
python - "$run_dir" <<'PY'
import json
from pathlib import Path
import sys

run_dir = Path(sys.argv[1])
report = json.loads((run_dir / "source_audit_report.json").read_text(encoding="utf-8"))
print(json.dumps({
    "source_name": report["source_name"],
    "decision": report["decision"],
    "status": report["status"],
    "rows_read": report["rows_read"],
    "rows_valid": report["rows_valid"],
    "rows_rejected": report["rows_rejected"],
    "partial_audit": report["partial_audit"],
    "max_rows": report["max_rows"],
}, indent=2, sort_keys=True))
PY

#!/usr/bin/env bash

set -euo pipefail

source .venv/bin/activate

export DATABASE_URL="sqlite:////tmp/worldcup2026_promotion_smoke.sqlite"
python -m src.db.init_db >/dev/null

run_dir=$(python -m src.ingestion.importers.historical_results_importer --input data/raw/sample/historical_results_sample.csv | tail -n 1)
bash scripts/promote_historical_results.sh "$run_dir"

for expected in promotion_report.json promotion_report.md; do
  if [[ ! -f "$run_dir/$expected" ]]; then
    echo "Missing $expected in $run_dir" >&2
    exit 1
  fi
done

echo "Promotion smoke test passed for $run_dir"

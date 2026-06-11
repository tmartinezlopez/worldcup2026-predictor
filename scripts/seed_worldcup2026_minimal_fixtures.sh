#!/usr/bin/env bash

set -euo pipefail

source .venv/bin/activate

sample_path="data/raw/sample/worldcup2026_fixtures_minimal_sample.csv"

if [[ ! -f "$sample_path" ]]; then
  echo "Missing sample file: $sample_path" >&2
  exit 1
fi

if ! bash scripts/db_healthcheck.sh >/dev/null 2>&1; then
  echo "Database is not reachable. Start it first with bash scripts/start_db.sh" >&2
  exit 1
fi

echo "WARNING: sample real-like fixtures are not official fixtures"

run_dir=$(python -m src.ingestion.importers.worldcup_fixtures_importer --input "$sample_path" | tail -n 1)

bash scripts/promote_worldcup_fixtures.sh "$run_dir"
bash scripts/promote_worldcup_fixtures.sh "$run_dir" --promote --allow-create-teams
bash scripts/assign_worldcup_batches.sh --promote

echo "run_dir=$run_dir"
echo "promotion_report_json=$run_dir/promotion_report.json"
echo "promotion_report_md=$run_dir/promotion_report.md"
bash scripts/db_counts.sh

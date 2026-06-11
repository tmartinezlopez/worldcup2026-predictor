#!/usr/bin/env bash

set -euo pipefail

batch_code="${1:-GROUP_STAGE_MD1}"
model_type="${2:-poisson}"

step() {
  echo
  echo "==> $1"
}

require_file() {
  local path="$1"
  local message="$2"
  if [[ ! -e "$path" ]]; then
    echo "$message" >&2
    exit 1
  fi
}

step "Checking local environment"
require_file ".venv" "Missing .venv. Run bash scripts/setup_dev.sh first."
require_file ".env" "Missing .env. Copy .env.example to .env first."

source .venv/bin/activate

step "Starting PostgreSQL services"
bash scripts/start_db.sh

step "Checking database health"
bash scripts/db_healthcheck.sh

step "Initializing database schema"
bash scripts/init_db.sh

step "Seeding sample historical results"
bash scripts/seed_sample_historical_results.sh

step "Seeding sample fixtures and batches"
bash scripts/seed_sample_fixtures.sh

step "Seeding sample team ratings"
bash scripts/seed_sample_team_ratings.sh

step "Running end-to-end batch orchestration"
bash scripts/run_batch.sh "$batch_code" "$model_type" --freeze --allow-after-cutoff

step "Exporting final batch report"
bash scripts/export_batch_report.sh "$batch_code" --include-drafts

step "Printing smoke summary"
python -m src.orchestration.smoke_summary --batch-code "$batch_code"

step "Printing database counts"
bash scripts/db_counts.sh

report_root="data/processed/final_reports/$batch_code"
step "Final report artifacts"
echo "$report_root/batch_report.html"
echo "$report_root/predictions.csv"
echo "$report_root/batch_report.json"
echo "$report_root/batch_report.md"

echo
echo "FINAL SMOKE PASSED"

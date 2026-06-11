#!/usr/bin/env bash

set -euo pipefail

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

step "Seeding sample team ratings"
bash scripts/seed_sample_team_ratings.sh

step "Seeding World Cup 2026 real-like minimal fixtures"
bash scripts/seed_worldcup2026_minimal_fixtures.sh

step "Detecting first generated group-stage batch"
batch_code=$(
  python - <<'PY'
from sqlalchemy import select
from src.db.connection import get_session
from src.db.models import Batch

with get_session() as session:
    batch = session.scalars(
        select(Batch)
        .where(Batch.code.like("GROUP_STAGE_%"))
        .order_by(Batch.first_match_start, Batch.code)
    ).first()
    if batch is None:
        raise SystemExit("No GROUP_STAGE_YYYYMMDD batch was generated")
    print(batch.code)
PY
)
echo "batch_code=$batch_code"

step "Running batch orchestration"
bash scripts/run_batch.sh "$batch_code" poisson --freeze --allow-after-cutoff

step "Running simulation"
bash scripts/run_simulation.sh "$batch_code" --runs 1000 --include-drafts

step "Exporting final batch report"
bash scripts/export_batch_report.sh "$batch_code" --include-drafts

step "Showing final artifacts"
bash scripts/show_final_artifacts.sh "$batch_code"

echo
echo "WORLDCUP2026 MINIMAL SMOKE PASSED"

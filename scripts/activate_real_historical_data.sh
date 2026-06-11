#!/usr/bin/env bash

set -euo pipefail

if [[ ! -d ".venv" ]]; then
  echo "Missing .venv. Run bash scripts/setup_dev.sh first." >&2
  exit 1
fi

if [[ ! -f ".env" ]]; then
  echo "Missing .env. Copy .env.example to .env first." >&2
  exit 1
fi

source .venv/bin/activate

echo "==> Starting PostgreSQL services"
bash scripts/start_db.sh

echo "==> Checking database health"
bash scripts/db_healthcheck.sh

echo "==> Initializing database schema"
bash scripts/init_db.sh

echo "==> Auditing real historical results"
bash scripts/audit_real_historical_results.sh

echo "==> Running latest historical promotion in dry-run mode"
bash scripts/promote_latest_historical_results.sh

echo "==> Building real-data activation report"
bash scripts/real_data_activation_report.sh

echo
echo "Review audit report and promotion dry-run report before any real promotion."
echo "If you accept the reports:"
echo "bash scripts/promote_latest_historical_results.sh --promote"
echo
echo "If this is only demo/dev and unresolved teams are acceptable:"
echo "bash scripts/promote_latest_historical_results.sh --promote --allow-create-teams"
echo
echo "REAL DATA ACTIVATION DRY RUN PASSED"

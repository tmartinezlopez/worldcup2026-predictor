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

echo "==> Running controlled real historical-results audit"
bash scripts/audit_real_historical_results.sh

echo
echo "Review audit report before promotion"
echo "To promote dry-run/latest: bash scripts/promote_latest_historical_results.sh"
echo "To promote real latest: bash scripts/promote_latest_historical_results.sh --promote"
echo
echo "REAL DATA SMOKE PASSED"

#!/usr/bin/env bash

set -euo pipefail

source .venv/bin/activate

if [[ $# -lt 1 ]]; then
  echo "Usage: bash scripts/promote_worldcup_fixtures.sh <run_dir> [flags...]" >&2
  exit 1
fi

run_dir="$1"
shift || true

args=(--run-dir "$run_dir" --dry-run)
for arg in "$@"; do
  if [[ "$arg" == "--promote" ]]; then
    args=(--run-dir "$run_dir" --promote)
  else
    args+=("$arg")
  fi
done

python -m src.ingestion.promoters.worldcup_fixtures_promoter "${args[@]}"

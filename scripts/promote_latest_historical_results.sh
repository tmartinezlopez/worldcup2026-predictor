#!/usr/bin/env bash

set -euo pipefail

source .venv/bin/activate

source_root="data/staging/imports/historical_results_importer"

if [[ ! -d "$source_root" ]]; then
  echo "No historical_results_importer runs found under $source_root" >&2
  exit 1
fi

latest_run_dir=""
while IFS= read -r run_dir; do
  if [[ -f "$run_dir/valid.jsonl" ]]; then
    latest_run_dir="$run_dir"
    break
  fi
done < <(find "$source_root" -mindepth 1 -maxdepth 1 -type d | sort -r)

if [[ -z "$latest_run_dir" ]]; then
  echo "Could not find a historical_results_importer run with valid.jsonl" >&2
  exit 1
fi

echo "latest_run_dir=$latest_run_dir"
echo "Running dry-run promotion first"
bash scripts/promote_historical_results.sh "$latest_run_dir"

run_real_promotion=false
extra_args=()
for arg in "$@"; do
  if [[ "$arg" == "--promote" ]]; then
    run_real_promotion=true
  else
    extra_args+=("$arg")
  fi
done

if [[ "$run_real_promotion" == "true" ]]; then
  echo "Running real promotion"
  bash scripts/promote_historical_results.sh \
    "$latest_run_dir" \
    --promote \
    "${extra_args[@]}"
fi

bash scripts/db_counts.sh

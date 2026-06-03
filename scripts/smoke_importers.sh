#!/usr/bin/env bash

set -euo pipefail

source .venv/bin/activate

declare -a MODULES=(
  "src.ingestion.importers.teams_importer data/raw/sample/teams_sample.csv teams_importer"
  "src.ingestion.importers.fixtures_importer data/raw/sample/fixtures_sample.csv fixtures_importer"
  "src.ingestion.importers.historical_results_importer data/raw/sample/historical_results_sample.csv historical_results_importer"
  "src.ingestion.importers.elo_importer data/raw/sample/elo_sample.csv elo_importer"
  "src.ingestion.importers.fifa_ranking_importer data/raw/sample/fifa_rankings_sample.csv fifa_ranking_importer"
  "src.ingestion.importers.players_importer data/raw/sample/players_sample.csv players_importer"
)

for entry in "${MODULES[@]}"; do
  read -r module input source_name <<<"$entry"
  run_dir=$(python -m "$module" --input "$input" | tail -n 1)
  echo "$source_name -> $run_dir"
  for expected in original.csv normalized.jsonl valid.jsonl rejected.jsonl validation_report.json review_report.md metadata.json; do
    if [[ ! -f "$run_dir/$expected" ]]; then
      echo "Missing $expected for $source_name" >&2
      exit 1
    fi
  done
done

echo "All importer smoke tests passed."

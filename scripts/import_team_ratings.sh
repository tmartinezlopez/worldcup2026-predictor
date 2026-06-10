#!/usr/bin/env bash

set -euo pipefail

source .venv/bin/activate

if [[ $# -lt 1 ]]; then
  echo "Usage: bash scripts/import_team_ratings.sh <csv>" >&2
  exit 1
fi

python -m src.ingestion.importers.team_ratings_importer --input "$1"

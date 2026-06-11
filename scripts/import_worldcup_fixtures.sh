#!/usr/bin/env bash

set -euo pipefail

source .venv/bin/activate

if [[ $# -lt 1 ]]; then
  echo "Usage: bash scripts/import_worldcup_fixtures.sh <csv>" >&2
  exit 1
fi

python -m src.ingestion.importers.worldcup_fixtures_importer --input "$1"

#!/usr/bin/env bash

set -euo pipefail

source .venv/bin/activate

if [[ $# -lt 1 ]]; then
  echo "Usage: bash scripts/run_simulation.sh <batch_code> [flags...]" >&2
  exit 1
fi

python -m src.simulation.monte_carlo --batch-code "$1" "${@:2}"

#!/usr/bin/env bash

set -euo pipefail

source .venv/bin/activate

if [[ $# -ne 1 ]]; then
  echo "Usage: bash scripts/evaluate_predictions.sh <model_run_id>" >&2
  exit 1
fi

python -m src.evaluation.evaluate_predictions --model-run-id "$1"

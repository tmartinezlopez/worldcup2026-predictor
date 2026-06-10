#!/usr/bin/env bash

set -euo pipefail

source .venv/bin/activate

if [[ $# -ne 2 ]]; then
  echo "Usage: bash scripts/freeze_predictions.sh <model_run_id> <batch_code>" >&2
  exit 1
fi

python -m src.prediction.freeze_predictions --model-run-id "$1" --batch-code "$2" --yes-freeze

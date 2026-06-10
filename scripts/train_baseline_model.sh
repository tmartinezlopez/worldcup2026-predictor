#!/usr/bin/env bash

set -euo pipefail

source .venv/bin/activate

if [[ $# -ne 2 ]]; then
  echo "Usage: bash scripts/train_baseline_model.sh <feature_set_id> <model_type>" >&2
  exit 1
fi

python -m src.models.train_baseline --feature-set-id "$1" --model-type "$2"

#!/usr/bin/env bash

set -euo pipefail

source .venv/bin/activate

if [[ $# -ne 1 ]]; then
  echo "Usage: bash scripts/build_feature_store.sh <batch_code>" >&2
  exit 1
fi

python -m src.features.build_feature_store --batch-code "$1"

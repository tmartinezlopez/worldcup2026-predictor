#!/usr/bin/env bash

set -euo pipefail

source .venv/bin/activate

if [[ $# -lt 2 ]]; then
  echo "Usage: bash scripts/run_batch.sh <batch_code> <model_type> [extra_flags...]" >&2
  exit 1
fi

python -m src.orchestration.run_batch --batch-code "$1" --model-type "$2" --yes-run "${@:3}"

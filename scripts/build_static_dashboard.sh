#!/usr/bin/env bash

set -euo pipefail

source .venv/bin/activate

if [[ $# -lt 1 ]]; then
  echo "Usage: bash scripts/build_static_dashboard.sh <batch_code> [flags...]" >&2
  exit 1
fi

python -m src.dashboard.static_dashboard --batch-code "$1" "${@:2}"

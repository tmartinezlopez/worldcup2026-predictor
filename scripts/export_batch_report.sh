#!/usr/bin/env bash

set -euo pipefail

source .venv/bin/activate

if [[ $# -lt 1 ]]; then
  echo "Usage: bash scripts/export_batch_report.sh <batch_code> [flags...]" >&2
  exit 1
fi

python -m src.reporting.export_batch_report --batch-code "$1" "${@:2}"

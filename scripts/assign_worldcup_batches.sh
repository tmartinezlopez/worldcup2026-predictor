#!/usr/bin/env bash

set -euo pipefail

source .venv/bin/activate

python -m src.ingestion.promoters.worldcup_batch_assigner --competition "FIFA World Cup 2026" "$@"

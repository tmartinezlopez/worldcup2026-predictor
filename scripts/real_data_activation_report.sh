#!/usr/bin/env bash

set -euo pipefail

source .venv/bin/activate

python -m src.data_quality.real_data_activation_report "$@"

#!/usr/bin/env bash

set -euo pipefail

bash scripts/final_smoke.sh
bash scripts/run_simulation.sh GROUP_STAGE_MD1 --runs 1000 --include-drafts
bash scripts/export_batch_report.sh GROUP_STAGE_MD1 --include-drafts
bash scripts/show_final_artifacts.sh

echo
echo "FINAL SMOKE WITH SIMULATION PASSED"

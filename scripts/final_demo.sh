#!/usr/bin/env bash

set -euo pipefail

bash scripts/final_smoke_with_simulation.sh
bash scripts/build_static_dashboard.sh GROUP_STAGE_MD1 --include-simulation
bash scripts/show_final_artifacts.sh GROUP_STAGE_MD1

echo
echo "FINAL DEMO PASSED"
echo "dashboard_html=data/processed/dashboard/GROUP_STAGE_MD1/index.html"

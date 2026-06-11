#!/usr/bin/env bash

set -euo pipefail

bash scripts/activate_real_historical_data.sh

echo
echo "Dry-run complete. Promote real data manually if reports look good."
echo "bash scripts/promote_latest_historical_results.sh --promote"
echo "bash scripts/rebuild_with_current_data.sh GROUP_STAGE_MD1 poisson"

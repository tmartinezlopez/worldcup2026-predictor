#!/usr/bin/env bash

set -euo pipefail

if [[ ! -d ".venv" ]]; then
  echo "Missing .venv. Run bash scripts/setup_dev.sh first." >&2
  exit 1
fi

source .venv/bin/activate

.venv/bin/ruff check src tests
.venv/bin/pytest -q
bash scripts/final_demo.sh
bash scripts/worldcup2026_minimal_smoke.sh
bash scripts/real_data_activation_report.sh
bash scripts/show_final_artifacts.sh GROUP_STAGE_MD1

git_status_output=$(git status --short || true)
if [[ -n "$git_status_output" ]]; then
  echo "WARNING: git worktree is not clean"
  printf '%s\n' "$git_status_output"
else
  echo "git_status=clean"
fi

echo
echo "FINAL RELEASE CHECK PASSED"

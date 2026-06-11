#!/usr/bin/env bash

set -euo pipefail

source .venv/bin/activate

batch_code="${1:-GROUP_STAGE_MD1}"
model_type="${2:-poisson}"

echo "==> Building feature store"
feature_output=$(bash scripts/build_feature_store.sh "$batch_code")
printf '%s\n' "$feature_output"
feature_set_id=$(printf '%s\n' "$feature_output" | awk -F= '/^feature_set_id=/{print $2}' | tail -n 1)

if [[ -z "$feature_set_id" ]]; then
  echo "Failed to capture feature_set_id from build_feature_store.sh output" >&2
  exit 1
fi

echo "==> Training baseline model"
model_output=$(bash scripts/train_baseline_model.sh "$feature_set_id" "$model_type")
printf '%s\n' "$model_output"
model_run_id=$(printf '%s\n' "$model_output" | awk -F= '/^model_run_id=/{print $2}' | tail -n 1)

if [[ -z "$model_run_id" ]]; then
  echo "Failed to capture model_run_id from train_baseline_model.sh output" >&2
  exit 1
fi

echo "==> Generating predictions"
bash scripts/generate_predictions.sh "$model_run_id"

echo "==> Evaluating predictions"
bash scripts/evaluate_predictions.sh "$model_run_id" || true

echo "==> Freezing predictions"
python -m src.prediction.freeze_predictions \
  --model-run-id "$model_run_id" \
  --batch-code "$batch_code" \
  --yes-freeze \
  --allow-after-cutoff

echo "==> Running simulation"
bash scripts/run_simulation.sh "$batch_code" --runs 1000 --include-drafts

echo "==> Exporting batch report"
bash scripts/export_batch_report.sh "$batch_code" --include-drafts

echo "==> Building static dashboard"
bash scripts/build_static_dashboard.sh "$batch_code" --include-simulation

echo "==> Showing final artifacts"
bash scripts/show_final_artifacts.sh "$batch_code"

echo
echo "REBUILD WITH CURRENT DATA PASSED"

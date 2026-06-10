#!/usr/bin/env bash

set -euo pipefail

show_file() {
  local label="$1"
  local path="$2"
  if [[ -f "$path" ]]; then
    echo "$label: $path"
  else
    echo "WARNING: missing $label at $path"
  fi
}

latest_dir() {
  local root="$1"
  if [[ ! -d "$root" ]]; then
    return 1
  fi
  find "$root" -mindepth 1 -maxdepth 1 -type d | sort | tail -n 1
}

report_root="data/processed/final_reports/GROUP_STAGE_MD1"

show_file "final_report_html" "$report_root/batch_report.html"
show_file "final_report_md" "$report_root/batch_report.md"
show_file "final_report_json" "$report_root/batch_report.json"
show_file "final_report_csv" "$report_root/predictions.csv"

if latest=$(latest_dir "data/processed/batch_runs"); then
  echo "latest_batch_run_report: $latest/batch_run_report.json"
else
  echo "WARNING: no batch_runs directory found"
fi

if latest=$(latest_dir "data/processed/model_reports"); then
  echo "latest_model_report: $latest/model_report.json"
else
  echo "WARNING: no model_reports directory found"
fi

if latest=$(latest_dir "data/processed/evaluation_reports"); then
  echo "latest_evaluation_report: $latest/evaluation_report.json"
else
  echo "WARNING: no evaluation_reports directory found"
fi

if latest=$(latest_dir "data/processed/freeze_reports"); then
  echo "latest_freeze_report: $latest/freeze_report.json"
else
  echo "WARNING: no freeze_reports directory found"
fi

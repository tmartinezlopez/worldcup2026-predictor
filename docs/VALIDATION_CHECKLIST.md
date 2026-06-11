# Validation Checklist

## Core Checks

```bash
source .venv/bin/activate
```

Expected: shell activates without error.

```bash
ruff check src tests
```

Expected: `All checks passed!`

```bash
pytest -q
```

Expected: full suite passes with no failures.

```bash
bash scripts/final_release_check.sh
```

Expected: release validation completes and prints `FINAL RELEASE CHECK PASSED`.

```bash
bash scripts/final_demo.sh
```

Expected: dashboard/static-report demo completes and prints `FINAL DEMO PASSED`.

```bash
bash scripts/worldcup2026_minimal_smoke.sh
```

Expected: real-like fixtures demo completes and prints `WORLDCUP2026 MINIMAL SMOKE PASSED`.

```bash
bash scripts/real_data_activation_report.sh
```

Expected: readiness report is generated and prints `output_dir=data/processed/real_data_reports`.

```bash
bash scripts/final_smoke.sh
```

Expected: sample flow completes, final reports are generated, and the script prints `FINAL SMOKE PASSED`.

```bash
bash scripts/real_data_smoke.sh
```

Expected: controlled real-data audit completes, prints review/promotion instructions, and ends with `REAL DATA SMOKE PASSED`.

```bash
git status --short
```

Expected: only intended local changes or generated artifacts under ignored paths. No accidental edits to `.env` or unrelated files.

## Expected Paths

- `data/processed/dashboard/GROUP_STAGE_MD1/index.html`
- `data/processed/dashboard/GROUP_STAGE_MD1/dashboard_data.json`
- `data/processed/final_reports/GROUP_STAGE_MD1/batch_report.html`
- `data/processed/final_reports/GROUP_STAGE_MD1/batch_report.json`
- `data/processed/final_reports/GROUP_STAGE_MD1/predictions.csv`

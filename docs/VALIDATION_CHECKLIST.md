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

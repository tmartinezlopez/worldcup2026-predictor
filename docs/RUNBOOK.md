# RUNBOOK

## Local setup

```bash
bash scripts/setup_dev.sh
cp .env.example .env
```

Update `.env` with local secrets before starting services.

## Start services

```bash
bash scripts/start_db.sh
```

## Check database connectivity

```bash
bash scripts/db_healthcheck.sh
```

## Initialize the schema

```bash
bash scripts/init_db.sh
```

## Stop services

```bash
bash scripts/stop_db.sh
```

## Reset development database

```bash
bash scripts/reset_db.sh
```

This removes the Docker volume used by the local PostgreSQL instance.

## Drop all tables without resetting Docker

```bash
python -m src.db.drop_db --yes-i-know
```

## Run quality checks

```bash
bash scripts/check.sh
```

Expected model artifacts for this phase:

- `data/processed/model_reports/<model_run_id>/model_report.json`
- `data/processed/model_reports/<model_run_id>/model_report.md`
- `data/processed/evaluation_reports/<evaluation_result_id>/evaluation_report.json`
- `data/processed/evaluation_reports/<evaluation_result_id>/evaluation_report.md`
- `data/processed/freeze_reports/<batch_or_timestamp>/freeze_report.json`
- `data/processed/freeze_reports/<batch_or_timestamp>/freeze_report.md`
- `data/processed/batch_runs/<batch_or_timestamp>/batch_run_report.json`
- `data/processed/batch_runs/<batch_or_timestamp>/batch_run_report.md`
- `data/processed/final_reports/<batch_code>/batch_report.json`
- `data/processed/final_reports/<batch_code>/batch_report.md`
- `data/processed/final_reports/<batch_code>/batch_report.html`
- `data/processed/final_reports/<batch_code>/predictions.csv`

## Identity resolution

- Approved aliases can resolve automatically to internal IDs.
- Unresolved entities should go to manual review before entering stable flows.
- Fuzzy matching only generates suggestions and never creates or approves entities.

## Safe staging smoke test

```bash
bash scripts/smoke_staging.sh
```

This creates a fake import run under `data/staging/imports/`, writes normalized and validated JSONL outputs, and generates validation reports.

The smoke test does not touch PostgreSQL.

## Importer smoke test

```bash
bash scripts/smoke_importers.sh
```

Example:

```bash
python -m src.ingestion.importers.historical_results_importer --input data/raw/sample/historical_results_sample.csv
```

## Source audit sample

```bash
bash scripts/audit_sample_source.sh
```

This audits the local historical-results sample and produces:

- `source_audit_report.json`
- `source_audit_report.md`
- `data/staging/source_registry.json`

## Historical results real-source audit

```bash
bash scripts/audit_historical_results_source.sh
```

You can also run it with a local file:

```bash
python -m src.ingestion.source_audits.historical_results_audit --local-file data/raw/sample/historical_results_sample.csv --no-download
```

The audit downloads the raw CSV in a controlled temporary file when internet is available, writes all outputs under `data/staging/imports/...`, and does not touch PostgreSQL.

## Historical results promotion

```bash
bash scripts/promote_historical_results.sh <run_dir>
```

```bash
bash scripts/promote_historical_results.sh <run_dir> --promote
```

```bash
bash scripts/promote_historical_results.sh <run_dir> --promote --allow-create-teams
```

Promotion runs in dry-run mode by default. `--promote` is required before any database write happens, and a `promotion_report` is written into the same `run_dir`.

## Development seed

```bash
bash scripts/seed_sample_historical_results.sh
```

```bash
bash scripts/db_counts.sh
```

```bash
bash scripts/seed_batches.sh
```

```bash
bash scripts/seed_sample_fixtures.sh
```

```bash
bash scripts/promote_fixtures.sh <run_dir> --promote --allow-create-teams
```

```bash
bash scripts/build_feature_store.sh <batch_code>
```

```bash
bash scripts/train_baseline_model.sh <feature_set_id> majority
```

```bash
bash scripts/train_baseline_model.sh <feature_set_id> logistic
```

```bash
bash scripts/train_baseline_model.sh <feature_set_id> poisson
```

```bash
bash scripts/generate_predictions.sh <model_run_id>
```

```bash
bash scripts/evaluate_predictions.sh <model_run_id>
```

```bash
bash scripts/freeze_predictions.sh <model_run_id> <batch_code>
```

```bash
bash scripts/run_batch.sh GROUP_STAGE_MD1 poisson
```

```bash
bash scripts/run_batch.sh GROUP_STAGE_MD1 poisson --freeze --allow-after-cutoff
```

```bash
bash scripts/export_batch_report.sh GROUP_STAGE_MD1 --include-drafts
```

```bash
bash scripts/export_batch_report.sh GROUP_STAGE_MD1 --official-only
```

## Final smoke

```bash
bash scripts/final_smoke.sh
```

```bash
bash scripts/final_smoke.sh GROUP_STAGE_MD1 poisson
```

## Real data minimal flow

```bash
bash scripts/real_data_smoke.sh
```

```bash
bash scripts/promote_latest_historical_results.sh
```

```bash
bash scripts/promote_latest_historical_results.sh --promote
```

```bash
bash scripts/promote_latest_historical_results.sh --promote --allow-create-teams
```

After seeding, you can inspect the loaded sample in DBeaver under:

- `Schemas -> public -> Tables -> teams`
- `Schemas -> public -> Tables -> matches`
- `Schemas -> public -> Tables -> batches`
- `Schemas -> public -> Tables -> batch_matches`
- `Schemas -> public -> Tables -> feature_sets`
- `Schemas -> public -> Tables -> match_features`
- `Schemas -> public -> Tables -> model_runs`
- `Schemas -> public -> Tables -> predictions`
- `Schemas -> public -> Tables -> evaluation_results`

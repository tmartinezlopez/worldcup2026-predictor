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

After seeding, you can inspect the loaded sample in DBeaver under:

- `Schemas -> public -> Tables -> teams`
- `Schemas -> public -> Tables -> matches`
- `Schemas -> public -> Tables -> batches`
- `Schemas -> public -> Tables -> batch_matches`

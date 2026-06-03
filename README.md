# worldcup2026-predictor

`worldcup2026-predictor` is the foundation for a dynamic prediction system for the FIFA World Cup 2026. The platform is designed to evaluate predictions in tournament batches, each one closing 10 minutes before the first match in that batch.

This initial phase focuses on a clean, reproducible, DB-first repository setup. It now includes a relational PostgreSQL schema foundation, but it still does not implement predictive models, real ingestion pipelines, or a dashboard.

## Architecture overview

- PostgreSQL is the source of truth for operational and analytical data.
- PostgreSQL and Adminer run in Docker for consistent local development.
- Python 3.11 runs locally inside `.venv`.
- Configuration is file-based and versioned under `config/`.
- Logging uses Python's standard `logging` module and writes to both console and file.

## Current scope

This phase includes:

- Repository structure and project configuration
- Dockerized database services
- Identity resolution foundation for aliases and fuzzy suggestions
- Safe staging and validation foundation for future data ingestion
- Base importers for local controlled files
- Source audit framework for controlled evaluation of future real data sources
- Historical results source audit support
- Controlled staging-to-database promotion for historical results
- Development seed support for sample historical results
- Controlled staging-to-database promotion for fixtures
- Development seed support for sample fixtures and batches
- Baseline operational scripts
- Initial documentation
- Minimal tests

This phase does not yet include:

- Predictive model implementation
- Real external data ingestion
- Database promotion from staging
- Tournament orchestration logic
- Dashboard or reporting UI

## Setup

1. Copy `.env.example` to `.env`.
2. Fill in real local secrets and connection values in `.env`.
3. Run the development setup:

```bash
bash scripts/setup_dev.sh
```

## Start the database

```bash
bash scripts/start_db.sh
```

Adminer will be available on `http://localhost:8080`.

## Check database connectivity

```bash
bash scripts/db_healthcheck.sh
```

## Initialize the schema

```bash
bash scripts/init_db.sh
```

## Drop all tables in development

```bash
python -m src.db.drop_db --yes-i-know
```

## Run checks

```bash
bash scripts/check.sh
```

## Safe staging

External data does not enter PostgreSQL yet. Imports must first go through staging, where the project writes normalized JSONL files plus machine-readable and human-readable validation reports.

Promotion into durable project datasets will be added in a future phase. This phase only prepares `normalized.jsonl`, `valid.jsonl`, `rejected.jsonl`, `validation_report.json`, `review_report.md`, and `metadata.json`.

## Source auditing

Real candidate sources are still not promoted into PostgreSQL. They are audited first using controlled local samples, and each audit produces explicit JSON and Markdown reports.

A local registry keeps the latest audit decision for each candidate source so we can document acceptance, warnings, or rejection before any real ingestion is enabled.

The audit layer still does not promote anything to the database.

Historical-results promotion now exists as a controlled step, but it still requires an explicit flag before any database write happens.

## Development seed

For local development only, `bash scripts/seed_sample_historical_results.sh` can load the sample historical results into PostgreSQL so the resulting `teams`, `team_aliases`, `competitions`, and `matches` are visible in tools like DBeaver.

This script intentionally uses `--allow-create-teams` during the real promote step, which is a development-only escape hatch and must not be treated as a production ingestion flow.

## Development fixture seed

For local development only, `bash scripts/seed_sample_fixtures.sh` can load the sample fixtures into PostgreSQL, seed minimal `batches`, and assign `batch_matches` so the scheduled sample is visible in DBeaver.

This script also uses `--allow-create-teams` during the real promote step. That is acceptable only for seed/dev workflows and must not be considered the future production fixture flow.

## Notes

- PostgreSQL is the source of truth for this project.
- The schema uses internal IDs across all entities and reserves JSON/JSONB for variable structures.
- Local Docker PostgreSQL uses port `5433` to avoid conflicts with other local instances.
- `data/raw/sample/` is intended for small versioned sample inputs only.

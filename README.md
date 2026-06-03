# worldcup2026-predictor

`worldcup2026-predictor` is the foundation for a dynamic prediction system for the FIFA World Cup 2026. The platform is designed to evaluate predictions in tournament batches, each one closing 10 minutes before the first match in that batch.

This initial phase focuses on a clean, reproducible, DB-first repository setup. It does not yet implement predictive models, real ingestion pipelines, or a dashboard.

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
- Baseline operational scripts
- Initial documentation
- Minimal tests

This phase does not yet include:

- Predictive model implementation
- Real external data ingestion
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

## Run checks

```bash
bash scripts/check.sh
```

## Notes

- PostgreSQL is the source of truth for this project.
- Local Docker PostgreSQL uses port `5433` to avoid conflicts with other local instances.
- `data/raw/sample/` is intended for small versioned sample inputs only.

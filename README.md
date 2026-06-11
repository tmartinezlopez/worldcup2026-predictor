# worldcup2026-predictor

`worldcup2026-predictor` is the foundation for a dynamic prediction system for the FIFA World Cup 2026. The platform is designed to evaluate predictions in tournament batches, each one closing 10 minutes before the first match in that batch.

This initial phase focuses on a clean, reproducible, DB-first repository setup. It now includes a relational PostgreSQL schema foundation, Feature Store v1, baseline model MVP support, Evaluation MVP, Official Freeze MVP, an end-to-end batch orchestrator MVP, a final report export MVP, a final end-to-end smoke flow, a minimal real-data audit/promotion upgrade, a Ratings / Rankings Minimal Input upgrade, a Real Fixtures Minimal upgrade, a Monte Carlo Simulation MVP, and a static dashboard viewer.

## Quick start

```bash
bash scripts/setup_dev.sh
cp .env.example .env
bash scripts/start_db.sh
bash scripts/final_smoke.sh
```

Open the main demo report at `data/processed/final_reports/GROUP_STAGE_MD1/batch_report.html`.

Optional real-data audit:

```bash
bash scripts/real_data_smoke.sh
```

Optional simulation demo:

```bash
bash scripts/final_smoke_with_simulation.sh
```

Optional static dashboard demo:

```bash
bash scripts/final_demo.sh
```

Open the static dashboard at `data/processed/dashboard/GROUP_STAGE_MD1/index.html`.

Optional real-data activation dry-run:

```bash
bash scripts/real_data_demo.sh
```

`real_data_demo.sh` audits and runs dry-run reporting only. It does not promote automatically.

Optional World Cup 2026 minimal fixtures demo:

```bash
bash scripts/worldcup2026_minimal_smoke.sh
```

More detail lives in [docs/SUBMISSION.md](/home/tomas/Documentos/formación/Hackathon%20Mundial/worldcup2026-predictor/docs/SUBMISSION.md) and [docs/RUNBOOK.md](/home/tomas/Documentos/formación/Hackathon%20Mundial/worldcup2026-predictor/docs/RUNBOOK.md).

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
- Feature Store v1 by batch from trusted PostgreSQL data
- Baseline Models MVP with draft-only prediction generation
- Evaluation MVP for finished matches only
- Official Freeze MVP with explicit cutoff-aware workflow
- End-to-end batch orchestrator MVP
- Final Report Export MVP
- Final end-to-end smoke
- Real Data Minimal Upgrade
- Monte Carlo Simulation MVP
- Ratings / Rankings Minimal Input
- Real Fixtures Minimal
- Stronger Baseline Features
- Static Dashboard / Viewer
- Real Data Activation Pack
- Baseline operational scripts
- Initial documentation
- Minimal tests

This phase does not yet include:

- Real external data ingestion
- Official World Cup 2026 fixtures ingestion
- Advanced model evaluation
- Tournament orchestration logic
- Server-side dashboard or framework-based UI

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

## Final validation

```bash
bash scripts/final_release_check.sh
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

## Final smoke

```bash
bash scripts/final_smoke.sh
```

`final_smoke.sh` continues to use versioned sample inputs. `real_data_smoke.sh` audits real historical results in a controlled way, but it does not promote them automatically.

`final_smoke.sh` now also seeds sample team ratings so the feature store can include ranking and rating-point inputs when they are available before the batch cutoff.

`data/raw/sample/worldcup2026_fixtures_minimal_sample.csv` is a real-like demo input for World Cup 2026 fixtures. It is intentionally not an official fixtures source.

## Codex guides

Persistent project guides for future Codex sessions live under [docs/guides](/home/tomas/Documentos/formación/Hackathon%20Mundial/worldcup2026-predictor/docs/guides).

## Notes

- PostgreSQL is the source of truth for this project.
- The schema uses internal IDs across all entities and reserves JSON/JSONB for variable structures.
- Local Docker PostgreSQL uses port `5433` to avoid conflicts with other local instances.
- `data/raw/sample/` is intended for small versioned sample inputs only.

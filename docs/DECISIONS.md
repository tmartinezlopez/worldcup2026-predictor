# DECISIONS

## Current decisions

- PostgreSQL is the source of truth.
- Docker is used for PostgreSQL and Adminer.
- Python runs locally with `.venv`.
- Python 3.11 is the recommended runtime.
- Dependencies are managed with `requirements.txt`.
- Basic project configuration lives in `pyproject.toml`.
- Black, Ruff, and pytest are the initial quality tools.
- Secrets are not committed; `.env.example` is versioned and `.env` is ignored.
- This phase excludes real ingestion, predictive models, and dashboards.

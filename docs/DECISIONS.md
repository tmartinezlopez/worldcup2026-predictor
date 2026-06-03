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
- The database schema is relational-first and created with SQLAlchemy models.
- All entities use internal IDs; names are never primary keys.
- JSONB is reserved for variable payloads and flexible configuration blocks.
- External and internal team ratings are stored separately.
- Constraints and supporting indexes are defined from the start.

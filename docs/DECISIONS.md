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
- `src/identity` is a transversal module shared by ingestion, validation, and prediction workflows.
- Teams and players have the highest-priority identity handling.
- Fuzzy matching only produces suggestions and never auto-resolves entities.
- Unresolved aliases do not create new entities automatically.
- Ambiguous identity cases are intentionally deferred to future human review workflows.
- Staging is mandatory before any future database promotion.
- JSONL is the primary normalized format inside staging.
- Valid and rejected records are stored separately during validation.
- `validation_report.json` is the machine-readable validation artifact.
- `review_report.md` is the human-readable review artifact.
- Validation is flexible but controlled; problematic rows are reported, not silently dropped.
- No data promotion to PostgreSQL happens in this phase.
- Importers are organized by source/type under `src/ingestion/importers`.
- Importers create staging artifacts only and do not promote to the database in this phase.
- Small sample files are allowed under `data/raw/sample` for repeatable local smoke tests.
- Any future real external source must pass a source audit before ingestion is enabled.
- Every real source must pass an explicit audit before it can be enabled.
- Rejected sources stay registered locally so the team does not repeat the same evaluation blindly.
- License, coverage, quality, and operational risks must be documented during source audit.
- No large real dataset is downloaded automatically in this phase.

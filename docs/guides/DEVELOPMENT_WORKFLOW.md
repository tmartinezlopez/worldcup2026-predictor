# DEVELOPMENT WORKFLOW

## Working style

- Keep each phase small and explicit.
- Validate every phase before treating it as stable.
- Prefer phase-scoped commits and pushes instead of mixing unrelated work.

## Quality checks

- Run `ruff check src tests`.
- Run `pytest -q`.
- Run the relevant smoke or seed scripts for the active phase when they exist.

## Git hygiene

- Review `git status` before committing.
- Do not commit `.env`.
- Do not commit `.venv`.
- Do not commit generated `data/staging` artifacts as stable source files.

## Main commands

```bash
bash scripts/setup_dev.sh
bash scripts/start_db.sh
bash scripts/db_healthcheck.sh
bash scripts/init_db.sh
bash scripts/check.sh
ruff check src tests
pytest -q
bash scripts/db_counts.sh
```

## Delivery expectation

- Keep functional logic changes aligned with the active phase only.
- Avoid adding features like models, feature store, or dashboard unless the phase explicitly requires them.

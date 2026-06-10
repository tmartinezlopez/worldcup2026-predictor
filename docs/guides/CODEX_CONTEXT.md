# CODEX CONTEXT

## Project objective

`worldcup2026-predictor` is a dynamic prediction system for the FIFA World Cup 2026.

The platform is designed to make predictions in evaluable tournament batches, not as one single monolithic prediction flow.

## Core tournament rule

- Predictions are evaluated by batches or tandas.
- Each batch closes 10 minutes before the first match in that batch.
- Every future feature must respect that cutoff rule.

## Operational foundations

- PostgreSQL is the source of truth.
- Python runs locally inside `.venv`.
- PostgreSQL and Adminer run in Docker.
- Secrets must not be committed to the repository.

## Delivery rules

- The system must stay reproducible and explainable.
- The project must avoid data leakage.
- Every phase must include tests.
- New work should not introduce predictive models, feature store logic, or dashboard work unless the active phase explicitly asks for it.

## Current implementation mindset

- Prefer small, phase-scoped changes.
- Respect the existing DB-first architecture.
- Preserve staging, validation, audit, and explicit promotion boundaries.

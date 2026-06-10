# ARCHITECTURE RULES

## `src/db`

- Owns SQLAlchemy models, schema helpers, connectivity, counts, and controlled DB seed utilities.
- Must define relational structure, constraints, indexes, and controlled DB operations.
- Must not contain ingestion logic for external sources.

## `src/identity`

- Owns normalization, alias resolution, and entity matching helpers.
- Must resolve names to internal IDs through approved aliases or explicit workflows.
- Must not silently create production entities from fuzzy matches.

## `src/staging`

- Owns staging paths, JSONL helpers, metadata, and import-run filesystem conventions.
- Must write staging artifacts before anything reaches PostgreSQL.
- Must not promote data to the database directly.

## `src/validation`

- Owns validation results, shared checks, dataset validation, and reporting.
- Must separate valid and rejected rows and produce reviewable artifacts.
- Must not bypass staging or write directly to production tables.

## `src/ingestion`

- Owns importers, source audit flows, staging entrypoints, and explicit promotion flows.
- Must move data through controlled steps: import, validate, audit when needed, then promote explicitly.
- Must not introduce direct source-to-DB writes.

## `src/features`

- Reserved for future feature engineering logic.
- Should build reproducible, cutoff-aware features from trusted DB data.
- Must not be implemented unless the active phase explicitly requests it.

## `src/models`

- Reserved for future model training and persistence logic.
- Should contain model-related artifacts only when model phases start.
- Must not be used early as a place for generic business logic.

## `src/prediction`

- Reserved for future inference and official prediction generation.
- Should respect batch cutoff rules and prediction freezing rules.
- Must not be implemented before the corresponding phase.

## `src/simulation`

- Reserved for future tournament and scenario simulation logic.
- Should remain separate from operational ingestion and DB foundation code.
- Must not be implemented before the corresponding phase.

## `src/evaluation`

- Reserved for future batch-based evaluation logic.
- Should compare frozen predictions against outcomes in a reproducible way.
- Must not be implemented before the corresponding phase.

## `src/orchestration`

- Reserved for future higher-level workflows and batch execution entrypoints.
- Should compose existing modules rather than duplicate their logic.
- Must not bypass validation, audit, or promotion controls.

## `src/utils`

- Owns generic shared utilities such as logging helpers.
- Should stay small and reusable.
- Must not become a catch-all for domain logic that belongs in a specific layer.

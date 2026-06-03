# MASTER_DOCUMENT

## A. What is predicted

The system is intended to predict World Cup 2026 outcomes in evaluable tournament batches. Each batch closes 10 minutes before the first scheduled match in that batch.

## B. Architecture

The platform follows a DB-first architecture. PostgreSQL acts as the source of truth, Python provides orchestration and analytical workflows, and Docker supplies reproducible local infrastructure.

## C. Database

PostgreSQL is the central persistence layer. The full schema is intentionally deferred to a later phase, but all future modules should assume database-backed state and reproducibility.

## D. Sources

External sources are not implemented yet. The project will later define curated, auditable, and version-aware inputs for fixtures, team identities, player data, and derived event datasets.

## E. Feature store

Feature generation is not implemented yet. The intended direction is a reproducible feature layer derived from trusted source data and persisted in PostgreSQL or adjacent controlled storage.

## F. Models

Predictive models are explicitly out of scope for this phase. Future work will start with simple baselines before any more sophisticated modeling stack is introduced.

## G. Simulation

Simulation is planned as a separate capability for tournament progression, scenario testing, and stress validation across batches and prediction windows.

## H. Evaluation

Evaluation will be batch-based, aligned with tournament timing and locking rules, with metrics and historical comparisons designed for reproducibility.

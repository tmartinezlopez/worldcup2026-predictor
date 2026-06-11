# Submission

## What This Project Is

`worldcup2026-predictor` is a DB-first prediction system foundation for the FIFA World Cup 2026. It is designed around evaluable tournament batches instead of one monolithic prediction flow.

## Problem It Solves

The project creates a controlled path from raw match data to explainable batch predictions. It reduces leakage risk, keeps database state auditable, and makes it possible to demo the full workflow locally without depending on a heavyweight dashboard.

## Batch-Based Approach

- Predictions are produced by batch or `tanda`.
- Every batch has a cutoff 10 minutes before its first match.
- Feature generation, prediction generation, and freeze decisions are all shaped around that anti-leakage boundary.

## Architecture Summary

- PostgreSQL is the source of truth.
- Python runs locally in `.venv`.
- Docker provides PostgreSQL and Adminer.
- Internal IDs are the canonical identifiers across entities.
- JSON/JSONB is used only for flexible payloads such as features, metrics, explanations, and reports.

## Pipeline

`staging -> validation -> audit -> promotion -> PostgreSQL -> feature store -> model -> predictions -> freeze -> report`

This separation keeps ingestion controlled, promotion explicit, and downstream artifacts reproducible.

## Local Demo

```bash
bash scripts/final_smoke.sh
```

This runs the sample-driven end-to-end flow and exports the final batch report.

## Real Data Audit

```bash
bash scripts/real_data_smoke.sh
```

This audits real historical results in a controlled way. It does not promote automatically.

## Generated Artifacts

- `data/processed/final_reports`
- `data/processed/batch_runs`
- `data/processed/model_reports`
- `data/processed/evaluation_reports`
- `data/processed/freeze_reports`

## What Is Real vs Demo

- Real architecture/pipeline:
  controlled staging, validation, audit, promotion, PostgreSQL-backed features, model training, simulation, and exported artifacts
- Real audit/promotion mechanisms:
  historical-results source audit and explicit promotion flows are implemented and dry-run-first
- Sample/demo fixtures:
  sample and controlled dev data still drive the most repeatable demo flows
- Real-like fixtures not official:
  World Cup fixture inputs are realistic demo assets but not official sources
- Real historical source activation remains manual:
  audit and readiness reporting exist, but promotion is still explicit and user-decided
- Predictions quality depends on promoted data:
  stronger trusted data in PostgreSQL improves coverage and usefulness, but current models remain baseline

## Implemented Today

- Relational schema foundation
- Identity and alias groundwork
- Safe staging and validation
- Historical results audit and controlled promotion
- Sample-based development seeds
- Feature Store v1
- Baseline model training
- Draft prediction generation
- Evaluation MVP
- Official freeze MVP
- Batch orchestrator MVP
- Final report export MVP
- Final smoke flow
- Minimal real-data audit and controlled latest-run promotion
- Monte Carlo simulation MVP
- Static dashboard viewer
- Real-data activation dry-run/reporting

## Consciously Out Of Scope

- Heavy server-side dashboard or web app
- Advanced model stack
- Large real-data automation beyond controlled audit/promotion
- Production-grade orchestration platform

## Current Limitations

- Sample datasets are intentionally small
- Models are baseline-only
- The delivered dashboard is static, not interactive/server-backed
- Real historical activation is still manual and explicit
- Official fixtures are not activated

## Why The Design Is Robust

- DB-first architecture keeps state centralized
- Internal IDs reduce identity ambiguity
- Audit and promotion steps make provenance reviewable
- Cutoff-aware design protects against leakage
- Official freeze is explicit rather than implicit
- Reports are generated artifacts, not the source of truth

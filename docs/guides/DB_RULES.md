# DB RULES

## Identity and keys

- Internal IDs are the canonical identifiers.
- Names must not be used as primary keys.
- Aliases are the bridge between external names and internal entities.

## Unresolved entities

- Unresolved entities must remain unresolved until they pass explicit identity handling.
- Fuzzy matching may suggest candidates but must not auto-create production entities.
- `--allow-create-teams` is allowed only in development or seed workflows.

## Schema design

- JSONB is reserved for variable payloads and flexible structures.
- External ratings and internal ratings stay separated.
- Constraints and indexes should be defined intentionally, not as an afterthought.

## Match and batch structure

- Matches are stored as first-class DB records.
- Batches represent evaluable tandas.
- `batch_matches` links batches to scheduled matches.

## Source-of-truth rule

- PostgreSQL is the system of record.
- Data should only arrive after controlled staging, validation, audit, and explicit promotion.

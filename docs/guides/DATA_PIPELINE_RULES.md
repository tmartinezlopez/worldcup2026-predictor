# DATA PIPELINE RULES

## Approved flow

`external source -> staging -> validation -> source audit -> promotion -> PostgreSQL`

## Staging rules

- External data must not go directly into PostgreSQL.
- The normalized staging format is JSONL.
- Staging outputs are written under `data/staging/imports/...`.
- `data/raw/` is reserved for small controlled samples unless a future phase defines something broader explicitly.

## Validation artifacts

- `normalized.jsonl` stores the normalized input rows.
- `valid.jsonl` stores rows that passed controlled validation.
- `rejected.jsonl` stores rows that failed validation or need rejection.
- `validation_report.json` is the machine-readable validation summary.
- `review_report.md` is the human-readable review summary.

## Source audit rules

- Candidate real sources must be audited before they can be treated as trusted.
- Source audit outputs must include machine-readable and human-readable reports.
- `source_audit_report.json` and `source_audit_report.md` document coverage, quality, and operational risk.

## Promotion rules

- Promotion is an explicit step after staging and validation.
- Promotion must use `dry-run` by default.
- Database writes require `--promote` explicitly.
- Promotion must produce `promotion_report.json` and `promotion_report.md`.

## Database boundary

- No source writes directly to PostgreSQL.
- No future shortcut should bypass staging, validation, and explicit promotion.

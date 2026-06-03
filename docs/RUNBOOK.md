# RUNBOOK

## Local setup

```bash
bash scripts/setup_dev.sh
cp .env.example .env
```

Update `.env` with local secrets before starting services.

## Start services

```bash
bash scripts/start_db.sh
```

## Stop services

```bash
bash scripts/stop_db.sh
```

## Reset development database

```bash
bash scripts/reset_db.sh
```

This removes the Docker volume used by the local PostgreSQL instance.

## Run quality checks

```bash
bash scripts/check.sh
```

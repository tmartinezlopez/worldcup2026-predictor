#!/usr/bin/env bash

set -euo pipefail

echo "Warning: this will remove the local development PostgreSQL volume."
read -r -p "Type 'reset' to continue: " confirmation

if [ "$confirmation" != "reset" ]; then
  echo "Reset cancelled."
  exit 0
fi

docker compose down -v
docker compose up -d

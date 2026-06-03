#!/usr/bin/env bash

set -euo pipefail

source .venv/bin/activate
black src tests
ruff check src tests
PYTHONPATH=. pytest -q

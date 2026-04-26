#!/bin/sh
set -eu

ITERATIONS="${1:-500}"
RESULTS_FILE="${2:-autoresearch-results-clean-v2.tsv}"

exec uv run python run_autoresearch_supervisor.py \
  --iterations "$ITERATIONS" \
  --results-file "$RESULTS_FILE"

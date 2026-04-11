#!/bin/sh
set -eu

ITERATIONS="${1:-500}"

exec uv run python run_autoresearch_supervisor.py --iterations "$ITERATIONS"

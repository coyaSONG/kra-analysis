#!/bin/sh
set -eu

mkdir -p .ralph/outputs

set -- \
  --config packages/scripts/autoresearch/clean_model_config.json \
  --output-dir .ralph/outputs

if [ "${RUNTIME_PARAMS_PATH:-}" != "" ]; then
  echo "run_rrx_experiment.sh does not support RUNTIME_PARAMS_PATH with seed_matrix_runner" >&2
  exit 2
fi

if [ "${MODEL_RANDOM_STATE:-}" != "" ]; then
  echo "run_rrx_experiment.sh does not support MODEL_RANDOM_STATE override with seed_matrix_runner" >&2
  exit 2
fi

uv run python packages/scripts/autoresearch/seed_matrix_runner.py "$@"

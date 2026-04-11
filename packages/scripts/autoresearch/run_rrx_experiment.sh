#!/bin/sh
set -eu

export PYTHONPATH="packages/scripts${PYTHONPATH:+:$PYTHONPATH}"

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

status=0
if uv run python packages/scripts/autoresearch/seed_matrix_runner.py "$@"; then
  status=0
else
  status=$?
fi

if [ "$status" -ne 0 ] && [ -f .ralph/outputs/holdout_seed_summary_report.json ]; then
  echo "seed_matrix_runner exited with $status but produced holdout summary; deferring rejection to metric gate" >&2
  exit 0
fi

exit "$status"

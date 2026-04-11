#!/bin/sh
set -eu

export PYTHONPATH="packages/scripts${PYTHONPATH:+:$PYTHONPATH}"

uv run pytest -q \
  packages/scripts/autoresearch/tests/test_rrx_propose.py \
  packages/scripts/autoresearch/tests/test_seed_matrix_runner.py \
  packages/scripts/autoresearch/tests/test_dataset_artifacts.py

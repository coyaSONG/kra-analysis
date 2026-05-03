#!/bin/sh
set -eu

export PYTHONPATH="packages/scripts${PYTHONPATH:+:$PYTHONPATH}"

uv run pytest -q \
  packages/scripts/autoresearch/tests/test_materialize_clean_dataset.py \
  packages/scripts/autoresearch/tests/test_research_clean.py \
  packages/scripts/autoresearch/tests/test_supervisor_invalidation_guard.py \
  packages/scripts/autoresearch/tests/test_rrx_propose.py \
  packages/scripts/autoresearch/tests/test_seed_matrix_runner.py \
  packages/scripts/autoresearch/tests/test_dataset_artifacts.py \
  packages/scripts/autoresearch/tests/test_t30_release_evaluation.py \
  packages/scripts/tests/test_operational_cutoff.py \
  packages/scripts/tests/test_prediction_input_field_registry.py \
  packages/scripts/tests/test_t30_release_contract.py \
  packages/scripts/tests/test_t30_release_gate.py \
  packages/scripts/tests/test_entry_change_snapshot_manifest.py

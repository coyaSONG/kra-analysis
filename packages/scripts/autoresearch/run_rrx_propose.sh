#!/bin/sh
set -eu

uv run python packages/scripts/autoresearch/rrx_propose.py \
  --config packages/scripts/autoresearch/clean_model_config.json

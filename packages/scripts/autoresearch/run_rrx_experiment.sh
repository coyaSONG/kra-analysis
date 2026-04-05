#!/bin/sh
set -eu

uv run python packages/scripts/autoresearch/research_clean.py \
  --config packages/scripts/autoresearch/clean_model_config.json \
  --output .ralph/outputs/research_clean.json

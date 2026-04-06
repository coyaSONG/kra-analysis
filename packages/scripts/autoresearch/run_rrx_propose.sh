#!/bin/sh
set -eu

export RRX_PROPOSER_MODE="${RRX_PROPOSER_MODE:-hybrid}"
export RRX_LLM_RATIO="${RRX_LLM_RATIO:-0.3}"
export RRX_LLM_CLIENT="${RRX_LLM_CLIENT:-codex}"
export RRX_LLM_TIMEOUT="${RRX_LLM_TIMEOUT:-180}"

uv run python packages/scripts/autoresearch/rrx_propose.py \
  --config packages/scripts/autoresearch/clean_model_config.json

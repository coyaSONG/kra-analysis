#!/bin/sh
set -eu

export PYTHONPATH="packages/scripts${PYTHONPATH:+:$PYTHONPATH}"

uv run python packages/scripts/autoresearch/extract_rrx_metric.py

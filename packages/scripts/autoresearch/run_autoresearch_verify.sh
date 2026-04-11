#!/bin/sh
set -eu

export PYTHONPATH="packages/scripts${PYTHONPATH:+:$PYTHONPATH}"

OUTPUT_DIR=".autoresearch/outputs"
SUMMARY_PATH="$OUTPUT_DIR/holdout_seed_summary_report.json"

mkdir -p "$OUTPUT_DIR"

uv run python packages/scripts/autoresearch/seed_matrix_runner.py \
  --config packages/scripts/autoresearch/clean_model_config.json \
  --output-dir "$OUTPUT_DIR" >/dev/null

uv run python - <<'PY'
import json
from pathlib import Path

summary_path = Path(".autoresearch/outputs/holdout_seed_summary_report.json")
if not summary_path.exists():
    raise SystemExit("missing summary report")

payload = json.loads(summary_path.read_text(encoding="utf-8"))
verification = payload.get("verification_verdict") or {}
lowest = verification.get("lowest_hit_rate")
if lowest is None:
    raise SystemExit("lowest_hit_rate missing from verification report")

print(float(lowest))
PY

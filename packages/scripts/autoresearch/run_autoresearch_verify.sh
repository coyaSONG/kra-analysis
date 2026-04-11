#!/bin/sh
set -eu

export PYTHONPATH="packages/scripts${PYTHONPATH:+:$PYTHONPATH}"

ROOT_DIR=".autoresearch"
RUNS_DIR="$ROOT_DIR/verify-runs"
RETENTION="${VERIFY_RUN_RETENTION:-5}"

mkdir -p "$RUNS_DIR"
RUN_DIR="$(mktemp -d "$RUNS_DIR/run.XXXXXX")"
OUTPUT_DIR="$RUN_DIR/outputs"
SUMMARY_PATH="$OUTPUT_DIR/holdout_seed_summary_report.json"

uv run python packages/scripts/autoresearch/seed_matrix_runner.py \
  --config packages/scripts/autoresearch/clean_model_config.json \
  --output-dir "$OUTPUT_DIR" >/dev/null

rm -rf "$ROOT_DIR/outputs"
ln -s "verify-runs/$(basename "$RUN_DIR")/outputs" "$ROOT_DIR/outputs"

if [ "$RETENTION" -gt 0 ] 2>/dev/null; then
  COUNT=0
  for old_run in $(ls -1dt "$RUNS_DIR"/run.* 2>/dev/null || true); do
    COUNT=$((COUNT + 1))
    if [ "$COUNT" -le "$RETENTION" ]; then
      continue
    fi
    rm -rf "$old_run"
  done
fi

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

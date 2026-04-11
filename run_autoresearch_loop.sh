#!/bin/sh
set -eu

PROMPT_FILE="${1:-AUTORESEARCH_PROMPT_500.txt}"
LOG_DIR=".autoresearch/runtime"
LOG_FILE="$LOG_DIR/codex-autoresearch.log"
LAST_FILE="$LOG_DIR/codex-autoresearch-last-message.txt"

mkdir -p "$LOG_DIR"

codex exec \
  -C "$(pwd)" \
  --dangerously-bypass-approvals-and-sandbox \
  --color never \
  --output-last-message "$LAST_FILE" \
  - < "$PROMPT_FILE" | tee "$LOG_FILE"

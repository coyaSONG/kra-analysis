#!/bin/bash
# Ralph - Long-running AI agent loop (snarktank/ralph 패턴)
# Usage: ./ralph.sh [--tool codex|claude|amp] [max_iterations]

set -e

TOOL="codex"
MAX_ITERATIONS=5

while [[ $# -gt 0 ]]; do
  case $1 in
    --tool) TOOL="$2"; shift 2 ;;
    --tool=*) TOOL="${1#*=}"; shift ;;
    *)
      if [[ "$1" =~ ^[0-9]+$ ]]; then MAX_ITERATIONS="$1"; fi
      shift ;;
  esac
done

if [[ "$TOOL" != "amp" && "$TOOL" != "claude" && "$TOOL" != "codex" ]]; then
  echo "Error: tool must be amp|claude|codex"; exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPT_FILE="$SCRIPT_DIR/RALPH_PROMPT.md"
PROGRESS_FILE="$SCRIPT_DIR/progress.txt"
LOG_DIR="$SCRIPT_DIR/.ralph-logs"
mkdir -p "$LOG_DIR"

if [ ! -f "$PROGRESS_FILE" ]; then
  echo "# Ralph Progress Log" > "$PROGRESS_FILE"
  echo "Started: $(date)" >> "$PROGRESS_FILE"
  echo "---" >> "$PROGRESS_FILE"
fi

echo "Starting Ralph - Tool: $TOOL - Max iterations: $MAX_ITERATIONS"

for i in $(seq 1 $MAX_ITERATIONS); do
  TS=$(date +%Y%m%d-%H%M%S)
  LOG_FILE="$LOG_DIR/iter-${i}-${TS}.log"
  LAST_FILE="$LOG_DIR/iter-${i}-${TS}-last.txt"

  echo ""
  echo "==============================================================="
  echo "  Ralph Iteration $i of $MAX_ITERATIONS ($TOOL)  -> $LOG_FILE"
  echo "==============================================================="

  case "$TOOL" in
    amp)
      OUTPUT=$(amp --dangerously-allow-all < "$PROMPT_FILE" 2>&1 | tee "$LOG_FILE") || true
      ;;
    claude)
      OUTPUT=$(claude --dangerously-skip-permissions --print < "$PROMPT_FILE" 2>&1 | tee "$LOG_FILE") || true
      ;;
    codex)
      OUTPUT=$(codex exec -C "$SCRIPT_DIR" \
        --dangerously-bypass-approvals-and-sandbox \
        --color never \
        --output-last-message "$LAST_FILE" \
        - < "$PROMPT_FILE" 2>&1 | tee "$LOG_FILE") || true
      ;;
  esac

  if grep -q "<promise>COMPLETE</promise>" "$LOG_FILE" 2>/dev/null; then
    echo ""
    echo "Ralph reported COMPLETE at iteration $i."
    exit 0
  fi

  echo "Iteration $i complete. Continuing..."
  sleep 2
done

echo ""
echo "Ralph reached max iterations ($MAX_ITERATIONS) without COMPLETE signal."
echo "See $PROGRESS_FILE."
exit 1

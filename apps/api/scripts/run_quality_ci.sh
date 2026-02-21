#!/usr/bin/env bash
set -euo pipefail

STAGE="${1:-all}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${API_ROOT}"

run_lint() {
  uv run ruff check --diff --exit-non-zero-on-fix .
  uv run ruff check .
}

run_format() {
  uv run ruff format --check .
}

run_typecheck() {
  bash "${API_ROOT}/../../.github/scripts/mypy_changed.sh"
}

run_unit() {
  uv run pytest -v -m unit --tb=short -o addopts=""
}

run_integration() {
  uv run pytest -v -m integration --tb=short --timeout=60 -o addopts=""
}

run_coverage() {
  uv run pytest -v -m unit
}

case "${STAGE}" in
  lint)
    run_lint
    ;;
  format)
    run_format
    ;;
  typecheck)
    run_typecheck
    ;;
  unit)
    run_unit
    ;;
  integration)
    run_integration
    ;;
  coverage)
    run_coverage
    ;;
  all)
    run_lint
    run_format
    run_typecheck
    run_unit
    run_integration
    run_coverage
    ;;
  *)
    echo "Unknown stage: ${STAGE}" >&2
    echo "Usage: $0 {lint|format|typecheck|unit|integration|coverage|all}" >&2
    exit 1
    ;;
esac

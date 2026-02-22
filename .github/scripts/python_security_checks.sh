#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-help}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
API_ROOT="${REPO_ROOT}/apps/api"
REQUIREMENTS_FILE="${API_ROOT}/requirements.txt"
EXCLUDE_PATHS="${API_ROOT}/tests,${API_ROOT}/.venv,${API_ROOT}/htmlcov,${API_ROOT}/.pytest_cache"
PIP_AUDIT_IGNORE_FILE="${REPO_ROOT}/.github/security/pip-audit-ignore.txt"
PIP_AUDIT_IGNORE_ARGS=()

usage() {
  cat <<'EOF'
Usage: python_security_checks.sh <mode>

Modes:
  report  Run pip-audit + bandit for visibility only (always exits 0).
  gate    Block CI on new pip-audit findings (baseline-aware) and Bandit HIGH/HIGH findings.
  help    Show this help message.

Notes:
  - report mode is intentionally non-blocking to avoid failing CI on known dependency issues.
  - gate mode uses .github/security/pip-audit-ignore.txt as a baseline.
  - IDs listed in the baseline are ignored; any new pip-audit vulnerability fails gate mode.
  - Bandit gate remains strict: HIGH severity + HIGH confidence.
EOF
}

require_uv() {
  if ! command -v uv >/dev/null 2>&1; then
    echo "Error: 'uv' is required but not found in PATH." >&2
    exit 1
  fi
}

load_pip_audit_ignore_args() {
  if [[ ! -f "${PIP_AUDIT_IGNORE_FILE}" ]]; then
    echo "Error: baseline ignore file not found: ${PIP_AUDIT_IGNORE_FILE}" >&2
    exit 1
  fi

  local raw_line=""
  local entry=""
  PIP_AUDIT_IGNORE_ARGS=()

  # Baseline file format: one vulnerability ID per line, '#' for comments.
  while IFS= read -r raw_line || [[ -n "${raw_line}" ]]; do
    entry="${raw_line%%#*}"
    entry="${entry#"${entry%%[![:space:]]*}"}"
    entry="${entry%"${entry##*[![:space:]]}"}"
    if [[ -n "${entry}" ]]; then
      PIP_AUDIT_IGNORE_ARGS+=(--ignore-vuln "${entry}")
    fi
  done < "${PIP_AUDIT_IGNORE_FILE}"
}

run_report() {
  require_uv

  echo "[python-security][report] Running pip-audit (report-only)"
  set +e
  uv run --project "${API_ROOT}" --with pip-audit pip-audit -r "${REQUIREMENTS_FILE}"
  pip_audit_rc=$?
  set -e
  if [[ ${pip_audit_rc} -ne 0 ]]; then
    echo "[python-security][report] pip-audit returned ${pip_audit_rc} (recorded; not gating)."
  fi

  echo "[python-security][report] Running bandit (report-only)"
  set +e
  uv run --project "${API_ROOT}" --with bandit bandit \
    -r "${API_ROOT}" \
    --severity-level low \
    --confidence-level low \
    -x "${EXCLUDE_PATHS}"
  bandit_rc=$?
  set -e
  if [[ ${bandit_rc} -ne 0 ]]; then
    echo "[python-security][report] bandit returned ${bandit_rc} (recorded; not gating)."
  fi
}

run_gate() {
  require_uv
  load_pip_audit_ignore_args

  local ignore_count=0
  ignore_count=$(( ${#PIP_AUDIT_IGNORE_ARGS[@]} / 2 ))

  echo "[python-security][gate] Running pip-audit with baseline ignore list (${ignore_count} IDs)"
  uv run --project "${API_ROOT}" --with pip-audit pip-audit \
    -r "${REQUIREMENTS_FILE}" \
    "${PIP_AUDIT_IGNORE_ARGS[@]}"

  echo "[python-security][gate] Blocking threshold: Bandit HIGH severity + HIGH confidence"
  uv run --project "${API_ROOT}" --with bandit bandit \
    -r "${API_ROOT}" \
    --severity-level high \
    --confidence-level high \
    -x "${EXCLUDE_PATHS}"
}

case "${MODE}" in
  report)
    run_report
    ;;
  gate)
    run_gate
    ;;
  help|-h|--help)
    usage
    ;;
  *)
    echo "Unknown mode: ${MODE}" >&2
    usage >&2
    exit 1
    ;;
esac

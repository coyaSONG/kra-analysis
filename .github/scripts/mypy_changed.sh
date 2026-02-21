#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "${REPO_ROOT}"

CHANGED_FILES_RAW=""

if [[ -z "${GITHUB_ACTIONS:-}" ]]; then
  CHANGED_FILES_RAW="$(git diff --name-only HEAD -- 'apps/api/**/*.py' 'apps/api/*.py' || true)"
else
  if [[ "${GITHUB_EVENT_NAME:-}" == "pull_request" && -n "${GITHUB_BASE_REF:-}" ]]; then
    git fetch --no-tags --depth=1 origin "${GITHUB_BASE_REF}"
    DIFF_BASE="origin/${GITHUB_BASE_REF}"
  elif git rev-parse --verify HEAD^ >/dev/null 2>&1; then
    DIFF_BASE="HEAD^"
  else
    DIFF_BASE=""
  fi

  if [[ -n "${DIFF_BASE}" ]]; then
    CHANGED_FILES_RAW="$(git diff --name-only "${DIFF_BASE}...HEAD" -- 'apps/api/**/*.py' 'apps/api/*.py' || true)"
  else
    CHANGED_FILES_RAW="$(git ls-files 'apps/api/**/*.py' 'apps/api/*.py' || true)"
  fi
fi

declare -a TARGETS=()
while IFS= read -r file; do
  [[ -n "${file}" ]] || continue
  [[ -f "${file}" ]] || continue
  TARGETS+=("${file#apps/api/}")
done <<< "${CHANGED_FILES_RAW}"

if [[ ${#TARGETS[@]} -eq 0 ]]; then
  echo "No changed Python files in apps/api. Skipping mypy."
  exit 0
fi

echo "Running mypy on changed files (${#TARGETS[@]}):"
printf ' - %s\n' "${TARGETS[@]}"

cd apps/api
uv run mypy "${TARGETS[@]}" --ignore-missing-imports --no-strict-optional --explicit-package-bases

#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "${REPO_ROOT}"

if grep -r "serviceKey\s*[:=]\s*[\"'][^$\"']*[\"']" . \
  --exclude-dir=.git \
  --exclude-dir=node_modules \
  --exclude-dir=data \
  --exclude="KRA_PUBLIC_API_GUIDE.md" | \
  grep -v "process\.env\|getenv\|VITE_\|import\.meta\.env\|\${.*}\|API_KEY"; then
  echo "Hardcoded API keys found!"
  exit 1
fi

if git ls-files | grep -E "^\.env$|^\.env\."; then
  echo ".env files committed!"
  exit 1
fi

if git ls-files | grep "^data/"; then
  echo "data/ files committed!"
  exit 1
fi

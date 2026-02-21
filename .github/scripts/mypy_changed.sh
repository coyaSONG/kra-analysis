#!/usr/bin/env bash
set -euo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/apps/api"
echo "Running mypy on full codebase..."
uv run mypy . --ignore-missing-imports --explicit-package-bases

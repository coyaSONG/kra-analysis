#!/bin/bash
set -euo pipefail

echo "KRA FastAPI API setup 시작"

if ! command -v uv >/dev/null 2>&1; then
    echo "uv가 없어 설치합니다..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
else
    echo "uv가 이미 설치되어 있습니다."
fi

echo "Python 3.13 확인 중..."
uv python install 3.13

echo "의존성 설치 중..."
uv sync --group dev

if [ ! -f .env ]; then
    cp .env.template .env
    echo ".env를 .env.template에서 생성했습니다. 실제 값으로 채워 주세요."
else
    echo ".env 파일이 이미 존재합니다."
fi

cat <<'EOF'

다음 단계:
1. `.env`에서 DATABASE_URL, SUPABASE_*, SECRET_KEY, VALID_API_KEYS를 채웁니다.
2. `uv run python3 scripts/apply_migrations.py`
3. `uv run pytest -q tests/integration/test_bootstrap_manifest.py tests/integration/test_startup_manifest_rejection.py -o addopts=''`
4. `uv run uvicorn main_v2:app --reload --port 8000`

주의:
- mixed legacy/unified schema state는 startup에서 fail closed 됩니다.
- legacy baseline이 섞인 DB 상태가 보이면 정리 후 manifest path를 다시 적용하세요.

문서:
- Swagger: http://localhost:8000/docs
- Supabase 설정 가이드: ./docs/SUPABASE_SETUP.md
EOF

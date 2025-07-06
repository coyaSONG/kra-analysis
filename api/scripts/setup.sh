#!/bin/bash

echo "🚀 KRA Race Prediction API 설정 시작..."

# uv 설치 확인
if ! command -v uv &> /dev/null; then
    echo "📦 uv가 설치되어 있지 않습니다. 설치를 시작합니다..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
else
    echo "✅ uv가 이미 설치되어 있습니다."
fi

# Python 3.11 설치 확인
echo "🐍 Python 3.11 확인 중..."
uv python install 3.11

# 의존성 설치
echo "📚 의존성 설치 중..."
uv sync --dev

# .env 파일 생성
if [ ! -f .env ]; then
    echo "🔧 .env 파일 생성 중..."
    cat > .env << EOF
# Supabase
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key  # Optional

# KRA API
KRA_API_KEY=your_kra_api_key

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=$(openssl rand -hex 32)

# Claude Code CLI
CLAUDE_CODE_PATH=$(which claude-code || echo "/usr/local/bin/claude-code")
EOF
    echo "⚠️  .env 파일이 생성되었습니다. 실제 값으로 업데이트해주세요!"
else
    echo "✅ .env 파일이 이미 존재합니다."
fi

echo ""
echo "✨ 설정이 완료되었습니다!"
echo ""
echo "다음 단계:"
echo "1. .env 파일을 열어 실제 API 키와 URL을 입력하세요"
echo "2. Supabase 대시보드에서 migrations/001_initial_schema.sql을 실행하세요"
echo "3. 서버를 실행하세요: uv run uvicorn api.main:app --reload"
echo ""
echo "📚 API 문서: http://localhost:8000/docs"
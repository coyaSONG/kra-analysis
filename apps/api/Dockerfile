# Python 3.11 + uv 기반 이미지
FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 및 빌드 요구사항 설치
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# uv 설치 (https://astral.sh/uv)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh -s -- -y \
    && echo 'export PATH="/root/.local/bin:$PATH"' >> /etc/profile
ENV PATH="/root/.local/bin:${PATH}"

# 프로젝트 메타파일만 복사하여 의존성 레이어 캐시 최적화
COPY pyproject.toml uv.lock ./

# 프로덕션 의존성만 설치 (가상환경은 /app/.venv)
ENV UV_PROJECT_ENVIRONMENT=/app/.venv
RUN uv sync --no-dev --frozen

# 애플리케이션 코드 복사
COPY . .

# 런타임 환경 변수
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:${PATH}"

# 포트 노출
EXPOSE 8000

# 기본 실행 명령 (uvicorn, .venv 사용)
CMD ["uvicorn", "main_v2:app", "--host", "0.0.0.0", "--port", "8000"]

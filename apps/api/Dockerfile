# Python 3.13 + uv 기반 이미지
FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.17 /uv /uvx /bin/

# 작업 디렉토리 설정
WORKDIR /workspace/apps/api

# 내보낸 프로덕션 의존성만 복사하여 의존성 레이어 캐시 최적화
COPY apps/api/requirements.txt ./

# 프로덕션 의존성만 설치 (가상환경은 /app/.venv)
ENV UV_PROJECT_ENVIRONMENT=/workspace/apps/api/.venv
RUN uv venv /workspace/apps/api/.venv \
    && uv pip install --python /workspace/apps/api/.venv/bin/python -r requirements.txt

# 애플리케이션 코드 복사
COPY apps/api ./
COPY packages/scripts/evaluation /workspace/packages/scripts/evaluation
COPY packages/scripts/ml /workspace/packages/scripts/ml
COPY packages/scripts/shared /workspace/packages/scripts/shared
COPY data/contracts /workspace/data/contracts

# 런타임 환경 변수
ENV PYTHONPATH=/workspace/apps/api
ENV PYTHONUNBUFFERED=1
ENV PATH="/workspace/apps/api/.venv/bin:${PATH}"

# 포트 노출
EXPOSE 8000

# 기본 실행 명령 (uvicorn, .venv 사용)
CMD ["uvicorn", "main_v2:app", "--host", "0.0.0.0", "--port", "8000"]

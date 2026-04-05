# KRA FastAPI API

이 앱은 현재 저장소의 활성 런타임입니다. 엔트리포인트는 `main_v2.py`이며, `collection`, `jobs`, `health`, `metrics` 라우터를 제공합니다.

## 현재 런타임 요약

- 프레임워크: FastAPI
- 데이터베이스: PostgreSQL + SQLAlchemy async ORM
- 캐시/상태 저장: Redis
- 작업 실행: 인프로세스 `asyncio` background task
- 외부 연동: KRA 공공데이터 API

중요: 과거 문서에 등장하는 Celery 기반 비동기 작업 구조는 현재 활성 구현이 아닙니다. 현재 `jobs` 실행은 `apps/api/infrastructure/background_tasks.py`를 통해 동작합니다.

## 설치와 실행

### 의존성 설치

```bash
cd apps/api
uv sync --group dev
```

저장소 루트에서 워크스페이스 의존성도 설치해야 합니다.

```bash
pnpm install
```

### 환경 변수

`apps/api/.env.template`를 복사해 `.env`를 만듭니다.

```bash
cd apps/api
cp .env.template .env
```

주요 항목:

- `DATABASE_URL`
- `REDIS_URL`
- `SECRET_KEY`
- `VALID_API_KEYS`
- `KRA_API_KEY`
- `KRA_API_VERIFY_SSL`

Supabase 연결과 DB 설정 상세는 [SUPABASE_SETUP.md](/Users/chsong/Developer/Personal/kra-analysis/apps/api/docs/SUPABASE_SETUP.md)에 정리했습니다.

### 개발 서버

```bash
cd apps/api
uv run uvicorn main_v2:app --reload --port 8000
```

또는 저장소 루트에서:

```bash
pnpm -w -F @apps/api dev
```

## 활성 엔드포인트

기본 URL은 `http://localhost:8000`입니다.

- `GET /` 기본 정보
- `GET /health`
- `GET /health/detailed`
- `GET /metrics`
- `POST /api/v2/collection/`
- `POST /api/v2/collection/async`
- `GET /api/v2/collection/status`
- `POST /api/v2/collection/result`
- `GET /api/v2/jobs/`
- `GET /api/v2/jobs/{job_id}`
- `POST /api/v2/jobs/{job_id}/cancel`

Swagger 문서:

- `http://localhost:8000/docs`
- `http://localhost:8000/redoc`

## 인증

보호된 엔드포인트는 `X-API-Key` 헤더를 사용합니다.

개발 환경에서는 `VALID_API_KEYS`를 설정하지 않으면 기본 테스트 키가 허용될 수 있습니다. 운영 환경에서는 반드시 명시적으로 설정해야 합니다.

예시:

```bash
curl -X POST http://localhost:8000/api/v2/collection/ \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: test-api-key-123456789' \
  -d '{"date":"20250622","meet":1,"race_numbers":[1,2,3]}'
```

## 작업과 수집 API 메모

- 동기 수집은 즉시 결과를 반환합니다.
- 비동기 수집은 `jobs` API로 추적합니다.
- `/api/v2/collection/result`는 경주 결과만 별도로 수집합니다.

현재 구조의 제약:

- 작업 실행기는 durable queue가 아니라 API 프로세스 내부 task입니다.
- startup은 manifest migration history와 mixed legacy/unified schema state를 request serving 전에 fail closed로 거부합니다.

## 데이터베이스와 마이그레이션

새 환경 bootstrap은 아래 한 경로만 사용합니다.

```bash
cd apps/api
uv run python3 scripts/apply_migrations.py
uv run pytest -q tests/integration/test_bootstrap_manifest.py tests/integration/test_startup_manifest_rejection.py -o addopts=''
uv run uvicorn main_v2:app --reload --port 8000
```

현재 schema truth는 `apps/api/infrastructure/migration_manifest.py`가 공개하는 active unified chain입니다. operator 경로는 모두 이 manifest-first bootstrap을 기준으로 하며, mixed legacy/unified state가 감지되면 앱이 fail closed 됩니다.

## 운영 점검 명령

```bash
cd apps/api
uv run pytest -q
uv run python scripts/check_collection_status_db.py
uv run python scripts/check_collection_status_db.py --date 20260214 --meet 1
```

## 프로젝트 구조

```text
apps/api/
├── main_v2.py
├── routers/
│   ├── collection_v2.py
│   ├── jobs_v2.py
│   ├── health.py
│   ├── metrics.py
│   └── race.py                 # legacy v1, 비활성
├── services/
│   ├── kra_collection_module.py
│   ├── collection_service.py
│   ├── result_collection_service.py
│   ├── job_service.py
│   ├── kra_api_service.py
│   └── race_service.py         # legacy v1, 비활성
├── infrastructure/
├── middleware/
├── models/
├── migrations/
├── scripts/
└── tests/
```

## 테스트

```bash
cd apps/api
uv run pytest -q
uv run pytest --cov=. --cov-report=html
```

저장소 루트에서도 실행할 수 있습니다.

```bash
pnpm -F @apps/api test
```

## 관련 문서

- [Legacy v1 정책](/Users/chsong/Developer/Personal/kra-analysis/apps/api/docs/LEGACY_V1_POLICY.md)
- [Supabase 설정 가이드](/Users/chsong/Developer/Personal/kra-analysis/apps/api/docs/SUPABASE_SETUP.md)
- [아키텍처 리메디에이션 ExecPlan](/Users/chsong/Developer/Personal/kra-analysis/docs/plans/2026-03-19-architecture-remediation-execplan.md)

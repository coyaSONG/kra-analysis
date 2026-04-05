# KRA 경마 데이터 수집 및 예측 분석

[![API Coverage](https://codecov.io/gh/chsong/kra-analysis/branch/main/graph/badge.svg?flag=api)](https://codecov.io/gh/chsong/kra-analysis)
[![CI](https://github.com/chsong/kra-analysis/actions/workflows/ci.yml/badge.svg)](https://github.com/chsong/kra-analysis/actions/workflows/ci.yml)

한국마사회(KRA) 데이터를 수집하고, 경주 전 데이터를 정리해 예측 실험과 평가에 사용하는 저장소입니다. 현재 운영 코어는 `apps/api`의 FastAPI 서버이며, 예측 평가와 프롬프트 개선 실험은 `packages/scripts`에 모여 있습니다.

## 현재 구조

이 저장소는 `pnpm` 워크스페이스를 사용하는 모노레포지만, 실제 런타임 중심은 `apps/api`입니다.

```text
kra-analysis/
├─ apps/
│  └─ api/                     # 활성 FastAPI 런타임
│     ├─ routers/              # collection, jobs, health, metrics
│     ├─ services/             # 수집/작업/외부 API 서비스
│     ├─ infrastructure/       # DB, Redis, background tasks
│     ├─ models/               # DTO / ORM 모델
│     ├─ middleware/           # logging, rate limit
│     ├─ migrations/           # SQL migration 파일
│     ├─ scripts/              # 점검/품질/마이그레이션 스크립트
│     └─ tests/
├─ packages/
│  ├─ scripts/                 # 평가, 프롬프트 개선, ML 실험 스크립트
│  ├─ shared-types/            # 공용 TypeScript 타입
│  ├─ eslint-config/
│  └─ typescript-config/
├─ docs/                       # 설계, 결정, 실행 계획 문서
└─ examples/                   # KRA API 응답 샘플
```

중요: 과거 문서에 등장하던 `apps/collector`는 현재 워크트리에 없습니다. 현재 활성 엔트리포인트는 `apps/api/main_v2.py`입니다.

## 핵심 기능

- `POST /api/v2/collection/`로 경주 데이터 수집
- `POST /api/v2/collection/async`로 비동기 수집 작업 생성
- `POST /api/v2/collection/result`로 경주 결과 수집
- `GET /api/v2/jobs/*`로 비동기 작업 조회/취소
- `GET /health`, `GET /health/detailed`, `GET /metrics`로 운영 상태 확인
- `packages/scripts`에서 평가, 프롬프트 개선, 실험 자동화 수행

## 빠른 시작

### 1. 의존성 설치

저장소 루트에서:

```bash
pnpm install
```

API Python 의존성 설치:

```bash
cd apps/api
uv sync --group dev
```

### 2. 환경 변수 준비

API 앱 디렉터리에서 템플릿을 복사합니다.

```bash
cd apps/api
cp .env.template .env
```

최소 확인 항목:

- `DATABASE_URL`
- `REDIS_URL`
- `SECRET_KEY`
- `VALID_API_KEYS`
- `KRA_API_KEY`

상세 설명은 [SUPABASE_SETUP.md](/Users/chsong/Developer/Personal/kra-analysis/apps/api/docs/SUPABASE_SETUP.md)를 참고하세요.

### 3. API 실행

저장소 루트에서:

```bash
pnpm -w -F @apps/api dev
```

또는 앱 디렉터리에서:

```bash
cd apps/api
uv run uvicorn main_v2:app --reload --port 8000
```

실행 후 확인:

- Swagger: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`
- Detailed health: `http://localhost:8000/health/detailed`
- Metrics: `http://localhost:8000/metrics`

## 주요 명령

저장소 루트에서:

```bash
pnpm dev
pnpm build
pnpm test
pnpm -w -F @apps/api dev
pnpm -F @apps/api test
pnpm run quality:api:ci
pnpm run quality:node:ci
pnpm run quality:scripts:ci
```

API 디렉터리에서:

```bash
uv run pytest -q
uv run python scripts/check_collection_status_db.py
uv run python scripts/apply_migrations.py
```

## 데이터베이스와 마이그레이션

현재 활성 스키마 기준선은 `apps/api/migrations/001_unified_schema.sql` 계열입니다. 초기 Supabase/legacy 경로를 전제로 한 오래된 SQL 파일도 저장소에 남아 있으므로, 새 환경을 올릴 때는 최신 문서와 현재 스크립트를 먼저 확인해야 합니다.

주의:

- 앱은 현재 `SQLAlchemy ORM + PostgreSQL` 중심입니다.
- `create_all()`과 SQL migration이 함께 존재하므로, 운영 환경에서는 migration 경로를 우선 확인해야 합니다.
- 상세 정리 계획은 [2026-03-19-architecture-remediation-execplan.md](/Users/chsong/Developer/Personal/kra-analysis/docs/plans/2026-03-19-architecture-remediation-execplan.md)에 정리되어 있습니다.

## 실험 및 평가 스크립트

`packages/scripts`에는 다음 실험 자산이 있습니다.

- `evaluation/` 프롬프트 평가
- `prompt_improvement/` 재귀 개선
- `ml/` 모델 학습/예측
- `autoresearch/` 자동 리서치 보조 로직

예시:

```bash
pnpm --filter=@repo/scripts run evaluate:v3 -- --help
pnpm --filter=@repo/scripts run improve:v5 -- --help
pnpm --filter=@repo/scripts run test
```

세부 구조는 [packages/scripts/README.md](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/README.md)를 참고하세요.

## 문서

- [API README](/Users/chsong/Developer/Personal/kra-analysis/apps/api/README.md)
- [프로젝트 개요](/Users/chsong/Developer/Personal/kra-analysis/docs/project-overview.md)
- [Knowledge Index](/Users/chsong/Developer/Personal/kra-analysis/docs/knowledge/INDEX.md)
- [아키텍처 리메디에이션 ExecPlan](/Users/chsong/Developer/Personal/kra-analysis/docs/plans/2026-03-19-architecture-remediation-execplan.md)
- [Legacy v1 정책](/Users/chsong/Developer/Personal/kra-analysis/apps/api/docs/LEGACY_V1_POLICY.md)

## 현재 주의사항

- 현재 작업 실행기는 durable queue가 아니라 인프로세스 `asyncio` 기반입니다.
- Redis 장애 허용, logging wiring, migration source of truth 등은 정리 작업이 진행 중입니다.
- 오래된 문서에는 Celery, `apps/collector`, legacy migration 설명이 남아 있을 수 있으니 최신 `docs/plans`와 `apps/api` 기준으로 판단해야 합니다.

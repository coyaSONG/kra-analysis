# KRA 경마 예측 시스템

[![API Coverage](https://codecov.io/gh/chsong/kra-analysis/branch/main/graph/badge.svg?flag=api)](https://codecov.io/gh/chsong/kra-analysis)
[![CI](https://github.com/chsong/kra-analysis/actions/workflows/ci.yml/badge.svg)](https://github.com/chsong/kra-analysis/actions/workflows/ci.yml)

한국마사회(KRA) 경마 데이터를 수집/보강하고, 프롬프트 기반 예측을 평가·개선하는 모노레포입니다.

## 프로젝트 구성

```
kra-analysis/
├─ apps/
│  └─ api/                       # FastAPI 수집/작업관리 API (@apps/api)
├─ packages/
│  ├─ scripts/                   # 평가/프롬프트 개선 스크립트 (@repo/scripts)
│  ├─ shared-types/              # 공용 TypeScript 타입
│  ├─ typescript-config/         # TS 공통 설정
│  └─ eslint-config/             # ESLint 공통 설정
├─ docs/                         # 설계/운영 문서
├─ examples/                     # API 응답 샘플
├─ turbo.json                    # Turborepo 설정
└─ pnpm-workspace.yaml
```

## 빠른 시작

### 1) 의존성 설치

```bash
# 루트
pnpm i

# Python 워크스페이스 의존성 동기화
uv sync --group dev
```

### 2) 환경 변수

```bash
cp apps/api/.env.example apps/api/.env
```

필수값(`DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`)을 채우고, 운영 환경에서는 `VALID_API_KEYS`를 반드시 설정합니다.

### 3) 개발 실행

```bash
# 루트에서 API 실행
pnpm -w -F @apps/api dev

# 또는 apps/api에서 직접 실행
cd apps/api
uv run uvicorn main_v2:app --reload --port 8000
```

## 주요 명령

### Monorepo

```bash
pnpm dev
pnpm build
pnpm test
```

### API 품질/테스트

```bash
pnpm run quality:api:lint
pnpm run quality:api:typecheck
pnpm run quality:api:unit
pnpm run quality:api:integration
pnpm run quality:api:coverage
```

### API 마이그레이션

```bash
cd apps/api
uv run alembic upgrade head
```

### 스크립트(평가/개선)

```bash
pnpm --filter=@repo/scripts run evaluate:help
pnpm --filter=@repo/scripts run evaluate:v3 -- --help
pnpm --filter=@repo/scripts run evaluate:predict-only -- --help
pnpm --filter=@repo/scripts run improve:help
pnpm --filter=@repo/scripts run improve:v5 -- --help
```

## API 운영 포인트

- Base URL: `http://localhost:8000`
- 문서: `/docs`, `/redoc`
- 헬스체크: `/health`, `/health/detailed`
- 메트릭: `/metrics` (`METRICS_ENABLED=true`일 때)
- 작업 러너 모드: `JOB_RUNNER_MODE=inprocess|celery`

Celery 모드 운영 시 worker를 별도 프로세스로 실행합니다.

```bash
cd apps/api
celery -A tasks.celery_app:celery_app worker --loglevel=info
```

## 운영 문서

- 시스템 개요: `docs/project-overview.md`
- SLO/SLI 정의: `docs/operations/slo.md`
- 장애 대응 Runbook: `docs/operations/runbook.md`
- API 상세 가이드: `apps/api/README.md`
- 통합 수집 API 설계: `docs/unified-collection-api-design.md`

## CI / 보안

- CI: `.github/workflows/ci.yml`
  - Python checks (Ruff, mypy, pytest, Alembic)
  - Node checks (workspace lint/typecheck/test)
  - Security checks (Gitleaks, npm audit, pip-audit, bandit)
- CodeQL: `.github/workflows/codeql.yml`

## 기여 가이드

커밋/코딩 규칙은 `AGENTS.md`의 `Repository Guidelines`를 따릅니다.

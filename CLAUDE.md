# CLAUDE.md

Claude Code 작업 시 필수 지침입니다.

## 프로젝트 개요
한국마사회(KRA) 경마 데이터 분석으로 삼복연승(1-3위) 예측 AI 시스템 개발

## 핵심 원칙

### 1. 프롬프트 작성
- XML 태그 구조화, Chain of Thought, Few-shot 예시 사용

### 2. 데이터 처리
- `win_odds=0` → 기권/제외마 (필터링 필수)
- enriched 데이터 우선 사용
- 상세 구조: `docs/enriched-data-structure.md`

### 3. 파일 관리
- **절대 삭제 금지**: .env, data/, KRA_PUBLIC_API_GUIDE.md
- **Git 제외**: data/ 폴더 (로컬 전용)

## 주요 명령어

### Python 스크립트 실행 (uv 사용)

```bash
# uv를 통한 직접 실행 (가상환경 자동 활성화)
uv run python3 packages/scripts/evaluation/evaluate_prompt_v3.py [버전] [프롬프트파일] [경주수] [병렬수]
uv run python3 packages/scripts/evaluation/predict_only_test.py [프롬프트파일] [날짜/all] [제한]
uv run python3 packages/scripts/prompt_improvement/recursive_prompt_improvement_v5.py [프롬프트] [날짜/all] [-i 반복] [-p 병렬] [-r 경주수/all]
uv run python3 packages/scripts/prompt_improvement/analyze_enriched_patterns.py

# Python 의존성 관리
uv sync                      # 전체 workspace 의존성 설치
uv sync --group dev          # 개발 의존성 포함 설치
uv add pandas                # 새 패키지 추가
uv remove pandas             # 패키지 제거
```

### 데이터 수집 (FastAPI API 서버)

```bash
# API 서버 실행
uv run python3 apps/api/main_v2.py

# 데이터 수집은 API 엔드포인트를 통해 Supabase DB에 저장
# POST /api/v2/collections/       - 동기 수집
# POST /api/v2/collections/async  - 비동기 수집
```

### pnpm 스크립트 (평가/개선)

```bash
# 프롬프트 평가
pnpm --filter=@repo/scripts run evaluate:v3 [버전] [프롬프트파일] [경주수] [병렬수]

# 예측 전용 테스트 (결과 비교 없음)
pnpm --filter=@repo/scripts run evaluate:predict-only [프롬프트파일] [날짜/all] [제한]

# 재귀 개선 (v5 - 최신)
pnpm --filter=@repo/scripts run improve:v5 [프롬프트] [날짜/all] [-i 반복] [-p 병렬] [-r 경주수/all]

# 데이터 패턴 분석
pnpm --filter=@repo/scripts run improve:analyze

# 개발 시 유용한 명령어
turbo watch dev                           # 파일 변경 감지 모드
pnpm test --filter=...@apps/api          # 변경된 패키지만 테스트
```

## 현재 상태
- 목표: 70% 이상 적중률
- v5 재귀 개선 시스템 구현 완료 (2025-06-22)
  - 프롬프트 파싱 시스템 (XML 태그 기반)
  - 인사이트 분석 엔진 (다차원 분석)
  - 동적 재구성 시스템 (실제 프롬프트 개선)
  - 예시 관리 시스템 (성과 추적 및 최적화)
  - **고급 기법 통합:**
    - Extended Thinking Mode (ultrathink) - 저성과 시 적용
    - 강화된 자가 검증 - 다단계 검증 프로세스
    - 토큰 최적화 - 효율적인 프롬프트 압축

## 참조 문서
- 프로젝트 상세: `docs/project-overview.md`
- API 가이드: `docs/KRA_PUBLIC_API_GUIDE.md` (또는 프로젝트 내 검색)
- Git 규칙: `docs/git-commit-convention.md`
- 재귀 개선: `docs/recursive-improvement-guide.md`
- v5 시스템: `packages/scripts/prompt_improvement/recursive_prompt_improvement_v5.py`

## 중요 규칙
- Python 실행: 항상 `python3` 사용
- 새 문서 생성 전 기존 문서 확인 필수
- 중복 내용 생성 금지
- Git 커밋 시 Claude 워터마크 제거 (Co-Authored-By 등)

<!-- GSD:project-start source:PROJECT.md -->
## Project

**KRA Analysis**

`KRA Analysis`는 한국마사회(KRA) 경주 데이터를 수집해 재사용 가능한 저장 구조로 정리하고, 그 데이터를 기반으로 예측 평가와 프롬프트 개선 실험을 반복하는 브라운필드 프로젝트다. 현재 운영 코어는 `apps/api`의 FastAPI 서버이고, 평가 및 실험 자동화는 `packages/scripts`에 분리되어 있다.

**Core Value:** KRA 경주 데이터를 수집, 저장, 조회, 재실험하는 핵심 계약이 런타임, 스키마, 문서에서 모두 같은 사실을 말해야 한다.

### Constraints

- **Tech stack**: Python 3.13+, FastAPI, SQLAlchemy async ORM, PostgreSQL, Redis, `uv`, `pnpm` — 현재 활성 런타임과 CI 체인을 유지해야 한다
- **Brownfield**: 이미 운영 중인 API와 실험 스크립트가 존재 — 기존 엔드포인트와 저장 구조를 무리하게 끊을 수 없다
- **API compatibility**: `collection`, `jobs`, `health`, `metrics` 경로는 유지되어야 한다 — 기존 호출자와 테스트 자산을 깨지 않기 위해서다
- **Operational safety**: Redis 장애, migration drift, background job 유실 가능성을 고려해야 한다 — 플랫폼 안정화가 현재 최우선 과제이기 때문이다
- **Documentation truthfulness**: 문서가 실제 코드와 어긋나면 안 된다 — 신규 기여자가 잘못된 구조를 학습하는 비용이 이미 발생하고 있기 때문이다
- **Version control**: 계획 문서는 git에 추적한다 — 현재 저장소 관례와 세션 복원성을 유지하기 위해서다
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.13 - API runtime and most domain logic live in `apps/api/**/*.py`, with offline evaluation and prompt-improvement workflows in `packages/scripts/**/*.py`.
- JavaScript / Node.js - Workspace orchestration and one utility fetcher live in `package.json`, `apps/api/package.json`, and `packages/scripts/evaluation/fetch_and_save_results.js`.
- YAML / JSON / TOML - Build, CI, linting, and dependency configuration live in `turbo.json`, `pnpm-workspace.yaml`, `.github/workflows/ci.yml`, `.github/workflows/codeql.yml`, `apps/api/pyproject.toml`, and `packages/scripts/pyproject.toml`.
## Runtime
- Python 3.13 is the declared baseline in `.python-version`, `apps/api/pyproject.toml`, `packages/scripts/pyproject.toml`, and `apps/api/Dockerfile`.
- Node.js 22 is the explicit CI/runtime baseline for workspace tooling in `.github/workflows/ci.yml`.
- `pnpm` 9.0.0 manages the monorepo workspace from `package.json`.
- `uv` manages Python dependency resolution and sync for `apps/api` and `packages/scripts` via `uv.lock`, `apps/api/pyproject.toml`, and `packages/scripts/pyproject.toml`.
- Lockfile: present in `pnpm-lock.yaml` and `uv.lock`.
## Frameworks
- FastAPI 0.118.0 - HTTP API framework used by `apps/api/main_v2.py` and the routers under `apps/api/routers/`.
- Uvicorn 0.37.0 - ASGI server used in `apps/api/main_v2.py`, `apps/api/package.json`, and `apps/api/Dockerfile`.
- Pydantic 2.11.9 + `pydantic-settings` 2.11.0 - configuration and DTO validation in `apps/api/config.py` and model modules under `apps/api/models/`.
- SQLAlchemy 2.0.43 + asyncpg 0.30.0 - async database access in `apps/api/infrastructure/database.py` and service modules under `apps/api/services/`.
- Pytest 8.x with `pytest-asyncio`, `pytest-cov`, and `pytest-timeout` - Python test runner configured in `apps/api/pyproject.toml` and exercised from `apps/api/tests/` and `packages/scripts/evaluation/tests/`.
- Turbo 2.5.5 - workspace task orchestration defined in `package.json`, `turbo.json`, and `apps/api/turbo.json`.
- Ruff - Python lint/format gate configured in `apps/api/pyproject.toml` and used by `apps/api/scripts/run_quality_ci.sh`.
- Mypy - Python type-checking configured in `apps/api/pyproject.toml`.
- ESLint + Prettier - Node/workspace formatting rules live in `.eslintrc.json`, `.prettierrc`, and `packages/eslint-config/package.json`.
- Docker - containerized API runtime is defined in `apps/api/Dockerfile`.
## Key Dependencies
- `supabase` 2.20.0 - secondary database/client integration wrapped in `apps/api/infrastructure/supabase_client.py`.
- `redis` 6.4.0 - cache, rate limiting, and background task state in `apps/api/infrastructure/redis_client.py`, `apps/api/middleware/rate_limit.py`, and `apps/api/infrastructure/background_tasks.py`.
- `httpx` 0.28.1 - outbound KRA API client transport in `apps/api/infrastructure/kra_api/core.py` and `apps/api/services/kra_api_service.py`.
- `python-jose` 3.5.0 - optional JWT creation and verification in `apps/api/dependencies/auth.py`.
- `structlog` 25.4.0 - structured JSON logging configured in `apps/api/main_v2.py` and used across the API.
- `prometheus-client` 0.23.1 - metrics support surfaced by `apps/api/routers/metrics.py` and runtime observability in `apps/api/bootstrap/runtime.py`.
- `pandas` 2.3.2 - collection/enrichment data shaping in `apps/api/services/collection_service.py` and `apps/api/services/collection_enrichment.py`.
- `psycopg2-binary` 2.9.11 - synchronous PostgreSQL access for evaluation scripts in `packages/scripts/shared/db_client.py`.
- `mlflow` 3.9.0 - experiment tracking used by `packages/scripts/evaluation/mlflow_tracker.py` and `packages/scripts/evaluation/evaluate_prompt_v3.py`.
- Local CLI integrations for `claude`, `codex`, and `gemini` are wrapped in `packages/scripts/shared/claude_client.py` and `packages/scripts/shared/llm_client.py`.
## Workspace Layout
- Root orchestrator in `package.json` and `turbo.json`.
- API app workspace in `apps/api/package.json` and `apps/api/pyproject.toml`.
- Shared Node config packages in `packages/typescript-config/package.json` and `packages/eslint-config/package.json`.
- Python-heavy script workspace in `packages/scripts/package.json` and `packages/scripts/pyproject.toml`.
- No frontend application package is detected under `apps/`; the workspace is backend- and scripting-centric.
- TypeScript is present as shared tooling configuration, not as a substantial application codebase.
## Configuration
- API settings are centralized in `apps/api/config.py` using `BaseSettings` with `.env` loading.
- Turbo passes shared env through from `turbo.json` and app-specific env through from `apps/api/turbo.json`.
- Environment example files exist at `apps/api/.env.example` and `apps/api/.env.template`; a local `apps/api/.env` file is also present.
- Monorepo task graph: `turbo.json`
- Workspace discovery: `pnpm-workspace.yaml`
- Root Node scripts: `package.json`
- API Python config: `apps/api/pyproject.toml`
- Script Python config: `packages/scripts/pyproject.toml`
- API container image: `apps/api/Dockerfile`
- Node lint/format config: `.eslintrc.json`, `.prettierrc`, `packages/eslint-config/package.json`
## Platform Requirements
- Python 3.13 with `uv` is required to run `apps/api` and `packages/scripts`.
- `pnpm` 9 and Node.js are required for Turbo-driven workspace commands from `package.json`.
- Local PostgreSQL-compatible access and Redis are expected by the API when running outside test mode, based on `apps/api/config.py` and `apps/api/infrastructure/database.py`.
- The deployable artifact detected in-repo is the API container defined by `apps/api/Dockerfile`, which runs `uvicorn main_v2:app`.
- Production assumes a remote PostgreSQL/Supabase database, Redis, and environment-injected secrets as enforced by `apps/api/config.py`.
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Evidence Sources
- Repository guidance in `AGENTS.md`
- JavaScript formatting rules in `.eslintrc.json` and `.prettierrc`
- Root Python tooling in `pyproject.toml`
- API-specific Python, mypy, pytest, and coverage settings in `apps/api/pyproject.toml`, `apps/api/pytest.ini`, and `apps/api/.coveragerc`
- Script-package Python tooling in `packages/scripts/pyproject.toml`
- Environment setup template in `apps/api/.env.template`
- FastAPI entrypoint and middleware wiring in `apps/api/main_v2.py`
- Settings and env loading in `apps/api/config.py`
- Router/service/module boundaries in `apps/api/routers/collection_v2.py`, `apps/api/services/collection_service.py`, `apps/api/services/job_service.py`, and `apps/api/bootstrap/runtime.py`
- Data-model patterns in `apps/api/models/collection_dto.py` and `apps/api/models/database_models.py`
- Authentication and error conventions in `apps/api/dependencies/auth.py`
- Script-package style in `packages/scripts/shared/llm_client.py`, `packages/scripts/shared/db_client.py`, `packages/scripts/evaluation/data_loading.py`, and `packages/scripts/prompt_improvement/jury_prompt_improver.py`
## Naming Patterns
- Python functions and variables use `snake_case`; classes use `PascalCase` per `AGENTS.md`.
- TypeScript, where present, should use `camelCase` for variables/functions and `PascalCase` for types/classes per `AGENTS.md`.
- API module filenames use `snake_case` and describe their layer role: `apps/api/services/collection_service.py`, `apps/api/routers/jobs_v2.py`, `apps/api/middleware/rate_limit.py`, `apps/api/dependencies/auth.py`.
- Request/response DTO classes are named by domain plus role: `CollectionRequest`, `CollectionResponse`, `ResultCollectionRequest` in `apps/api/models/collection_dto.py`; `JobListResponse` and related DTOs in `apps/api/models/job_dto.py`.
- Persistence models use singular `PascalCase` class names and plural table names: `Race`, `Job`, `Prediction`, `APIKey` in `apps/api/models/database_models.py`.
- Compatibility fields are labeled explicitly with legacy-oriented names instead of silent reuse: `job_kind_v2`, `lifecycle_state_v2` in `apps/api/models/database_models.py`, and compatibility properties like `race_date` and `race_no` in `apps/api/models/database_models.py`.
- Service-layer helper aliases use descriptive suffixes to disambiguate imports: `analyze_weather_impact_helper`, `preprocess_data_helper` in `apps/api/services/collection_service.py`.
- Script-package modules also use `snake_case`, but import path setup is often manual via `sys.path.insert(...)` in `packages/scripts/evaluation/evaluate_prompt_v3.py`, `packages/scripts/evaluation/predict_only_test.py`, and `packages/scripts/prompt_improvement/jury_prompt_improver.py`.
## Code Style
- JavaScript formatting is 2-space indent, single quotes, semicolons, trailing commas on multiline structures, max length 120, and ESM modules via `.eslintrc.json` and `.prettierrc`.
- Python uses Ruff with line length 88 and target `py313` in `pyproject.toml` and `apps/api/pyproject.toml`.
- Ruff lint sets include `E`, `W`, `F`, `I`, `B`, `C4`, and `UP` in both `pyproject.toml` and `apps/api/pyproject.toml`.
- Mypy is configured only for the API package in `apps/api/pyproject.toml`, and the settings are intentionally permissive: `disallow_untyped_defs = false`, `ignore_missing_imports = true`.
- Python files commonly begin with a module docstring, even for small modules, for example `apps/api/main_v2.py`, `apps/api/config.py`, `apps/api/middleware/logging.py`, and `packages/scripts/shared/llm_client.py`.
- Import grouping is consistent: stdlib first, third-party second, local application imports last. See `apps/api/services/collection_service.py`, `apps/api/dependencies/auth.py`, and `packages/scripts/shared/db_client.py`.
- Newer modules prefer modern typing syntax such as `list[str]`, `dict[str, Any]`, `str | None`, and Python 3.12 type alias syntax (`type DispatchHandler = ...`) as seen in `apps/api/services/job_service.py`.
- Value objects and internal contracts increasingly use `@dataclass`, often with `frozen=True` and `slots=True`, for example `apps/api/policy/principal.py`, `apps/api/services/kra_collection_module.py`, and `apps/api/infrastructure/kra_api/core.py`.
- Older Pydantic request models still use v1-style `@validator` and `class Config` patterns in `apps/api/models/collection_dto.py`, even though the runtime depends on Pydantic v2 in `apps/api/pyproject.toml`.
## Module and Layer Patterns
- Domain logic should stay in `services/`; HTTP and I/O should stay in the API layer per `AGENTS.md`.
- FastAPI setup is centralized in `apps/api/main_v2.py`; route modules are mounted there and should not duplicate app construction elsewhere.
- HTTP boundary code lives in `apps/api/routers/*.py` and stays relatively thin. Routers mostly validate inputs, acquire dependencies, translate exceptions to `HTTPException`, and delegate to services or workflow modules, as in `apps/api/routers/collection_v2.py` and `apps/api/routers/jobs_v2.py`.
- Business logic lives under `apps/api/services/*.py`; these modules coordinate adapters, infrastructure, database sessions, and policy code. `apps/api/services/collection_service.py` and `apps/api/services/job_service.py` are canonical examples.
- Shared infrastructure is isolated under `apps/api/infrastructure/*.py` for DB, Redis, KRA API transport, and background task plumbing.
- Request-scoped and app-scoped cross-cutting concerns are separated into `apps/api/middleware/*.py` and `apps/api/bootstrap/runtime.py`.
- Script-package code under `packages/scripts` is flatter and less layered than the API. It often favors direct imports and command-oriented modules over explicit service boundaries, as seen in `packages/scripts/evaluation/data_loading.py` and `packages/scripts/prompt_improvement/jury_prompt_improver.py`.
## Typing and Data-Model Patterns
- Use Python 3.13+ across the repo per `pyproject.toml`, `apps/api/pyproject.toml`, and `packages/scripts/pyproject.toml`.
- FastAPI request/response payloads are modeled with Pydantic `BaseModel` plus rich `Field(...)` metadata for schema descriptions in `apps/api/models/collection_dto.py` and `apps/api/models/job_dto.py`.
- SQLAlchemy models use typed declarative mappings with `Mapped[...]` and `mapped_column(...)` rather than untyped legacy ORM style. See `apps/api/models/database_models.py`.
- The code distinguishes external KRA payload shape from internal shape. External API fields stay camelCase in DTOs like `HorseData.chulNo` and `RaceInfo.rcDate` in `apps/api/models/collection_dto.py`, while internal processing and persistence use `snake_case` fields like `race_number`, `result_status`, and `created_by` in `apps/api/models/database_models.py`.
- Field-shape translation is explicit rather than implicit. `convert_api_to_internal` in `apps/api/utils/field_mapping.py` and adapter logic in `apps/api/adapters/kra_response_adapter.py` are the expected bridge points.
- Backward compatibility is preserved inside models rather than through duplicated tables or DTOs. Examples include `Race.race_date`, `Race.race_no`, and `Race.status` compatibility properties in `apps/api/models/database_models.py`.
- Script-package code frequently uses small dataclasses for in-memory contracts, such as `LLMResponse` in `packages/scripts/shared/llm_client.py` and `RaceEvaluationDataLoader` in `packages/scripts/evaluation/data_loading.py`.
## Configuration and Environment Handling
- Real secrets belong in `.env` files and must not be committed, with `apps/api/.env.template` as the setup template per `AGENTS.md`.
- Turbo passes through `KRA_*`, `SUPABASE_*`, `REDIS_*`, `DATABASE_URL`, `SECRET_KEY`, `CELERY_*`, and `PG*` environment variables via `turbo.json`.
- API configuration is centralized in `apps/api/config.py` via `Settings(BaseSettings)`. Modules usually import the global singleton `settings` rather than instantiating settings ad hoc.
- The API settings object uses env aliases for some fields, for example `SUPABASE_ANON_KEY` and `SUPABASE_SERVICE_ROLE_KEY` in `apps/api/config.py`.
- Production guardrails are enforced during settings load, not deferred until first use. `apps/api/config.py` raises immediately for unsafe defaults such as the dev `SECRET_KEY`, missing `VALID_API_KEYS`, insecure `DATABASE_URL`, or placeholder Supabase values.
- Tests mutate the global config singleton instead of rebuilding the app with isolated settings providers. `_apply_test_settings_to_global()` in `apps/api/tests/platform/fixtures.py` is the established pattern.
- Script-package code does not reuse `Settings(BaseSettings)`. `packages/scripts/shared/db_client.py` reads `apps/api/.env` directly with `dotenv_values`, then rewrites `postgresql+asyncpg://` URLs for `psycopg2`.
- Because script modules often load env state directly and patch `sys.path`, future code in `packages/scripts` should follow the existing explicit-path style unless the package layout is first normalized.
## Error Handling Conventions
- Router boundaries usually catch broad exceptions, log them, and convert them to `HTTPException`. Examples: `apps/api/routers/collection_v2.py` and `apps/api/routers/jobs_v2.py`.
- Service boundaries wrap DB mutations in `try/except`, log structured error details, and `rollback()` before re-raising. `apps/api/services/job_service.py` is the clearest reference.
- Optional dependencies are often fail-open instead of hard-failing the request path. Redis initialization in `apps/api/main_v2.py`, cache access in `apps/api/infrastructure/redis_client.py`, and rate limiting in `apps/api/middleware/rate_limit.py` all degrade gracefully when Redis is unavailable.
- Global exception handling in `apps/api/main_v2.py` generates an `error_id` and returns a generic 500 payload instead of leaking stack traces.
- The API distinguishes user-visible validation errors from operational backend errors. `apps/api/dependencies/auth.py` raises `401` for missing/invalid API keys, `429` for quota exhaustion, and `503` when the auth backend is unavailable.
- Script-package modules are less uniform: some return `None` and print errors (`packages/scripts/evaluation/data_loading.py`), while others rely on stdlib logging (`packages/scripts/prompt_improvement/jury_prompt_improver.py`). New script code should match the local module style rather than importing API patterns blindly.
## Logging Conventions
- Logging is configurable via env-backed settings like `log_level`, `log_format`, and `log_file` in `apps/api/config.py`.
- The API standard is `structlog`. Most runtime modules define `logger = structlog.get_logger()` at module scope, for example `apps/api/main_v2.py`, `apps/api/dependencies/auth.py`, `apps/api/services/collection_service.py`, and `apps/api/infrastructure/database.py`.
- Structured key-value logging is preferred over interpolated strings when context matters. Good examples: `logger.error("Unhandled exception", error_id=..., path=..., method=...)` in `apps/api/main_v2.py` and `logger.warning("Rate limit degraded: bypassing due to Redis failure", error=str(e))` in `apps/api/middleware/rate_limit.py`.
- Some modules still mix in f-string logging, especially older router/service code such as `apps/api/routers/collection_v2.py` and parts of `apps/api/main_v2.py`. For consistency, new API code should prefer structured event names plus keyword fields.
- Request logging redacts sensitive fields before emission. `_mask_sensitive_fields()` and `_mask_sensitive_value()` in `apps/api/middleware/logging.py` are the repository standard for masking headers, query params, and tokens.
- Script-package logging is mixed: `packages/scripts/prompt_improvement/jury_prompt_improver.py` uses stdlib `logging`, `packages/scripts/evaluation/data_loading.py` uses `print`, and shared utilities are not consistently structured.
## Comments and Documentation Style
- Short module docstrings are common and often bilingual in effect: Korean business context with English technical terms. See `apps/api/main_v2.py`, `apps/api/config.py`, and `packages/scripts/shared/llm_client.py`.
- Inline comments are used to explain compatibility, migration, and failure-mode rationale rather than trivial operations. Examples include Redis fail-open notes in `apps/api/middleware/rate_limit.py` and legacy compatibility properties in `apps/api/models/database_models.py`.
- Example payloads live inside DTO classes using `json_schema_extra` rather than external docs for request/response bodies. `apps/api/models/collection_dto.py` and `apps/api/models/job_dto.py` are the references.
## Practical Guidance for Future Changes
- Put new HTTP endpoints in `apps/api/routers/` and keep them thin; delegate orchestration to `apps/api/services/` or workflow modules like `apps/api/services/kra_collection_module.py`.
- Model public API payloads with Pydantic models in `apps/api/models/`, and describe fields with `Field(...)`.
- Model persistence with typed SQLAlchemy models in `apps/api/models/database_models.py` style; use `Mapped[...]`, `mapped_column(...)`, and explicit JSON field types.
- Use `structlog` and keyword fields in new API modules. Avoid logging raw API keys, JWTs, passwords, or service keys; reuse masking helpers from `apps/api/middleware/logging.py`.
- Read config through `config.settings` inside the API package. Do not introduce ad hoc `os.getenv(...)` calls in new API modules unless the value is intentionally outside the settings model.
- If you add new script-package modules under `packages/scripts`, follow the local reality: small command-oriented modules, explicit dataclasses, and direct tests. If you need reusable config or imports there, consider normalizing packaging first because current script code frequently depends on `sys.path.insert(...)`.
- Treat TypeScript lint/format configs as repo-level scaffolding only. No active `*.ts` or `*.tsx` source files were detected in the checked-out working tree outside `.worktrees/`, so Python conventions are the operative standard here.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- Runtime composition is centralized in `apps/api/main_v2.py`; the application mounts routers, middleware, DB session factory, and a small runtime facade.
- Request handling is layered as router -> auth dependency/policy -> service facade/service -> infrastructure/model, with `AsyncSession` injected at the router boundary from `apps/api/infrastructure/database.py`.
- Background execution is not an external worker system; `apps/api/infrastructure/background_tasks.py` runs `asyncio.create_task()` jobs in-process and persists best-effort task state in Redis.
- External KRA calls are wrapped twice: transport policy and retry live in `apps/api/infrastructure/kra_api/core.py`, while endpoint-specific methods live in `apps/api/services/kra_api_service.py`.
- Persistence is SQLAlchemy-first. `apps/api/models/database_models.py` is the canonical schema for active API flows, while `apps/api/infrastructure/supabase_client.py` exists but is not in the active HTTP request path.
## Layers
- Purpose: Build the FastAPI app, register middleware and routers, manage startup/shutdown.
- Location: `apps/api/main_v2.py`, `apps/api/bootstrap/runtime.py`
- Contains: `create_app()`, lifespan startup/shutdown, `AppRuntime`, `ObservabilityFacade`
- Depends on: `apps/api/config.py`, `apps/api/routers/*.py`, `apps/api/infrastructure/database.py`, `apps/api/infrastructure/redis_client.py`, `apps/api/infrastructure/background_tasks.py`, `apps/api/middleware/*.py`
- Used by: `uvicorn main_v2:app`, tests that call `create_app()` from `apps/api/tests/platform/fixtures.py`
- Purpose: Define request/response contracts and map HTTP calls onto services.
- Location: `apps/api/routers/collection_v2.py`, `apps/api/routers/jobs_v2.py`, `apps/api/routers/health.py`, `apps/api/routers/metrics.py`
- Contains: FastAPI route handlers, response shaping, `Depends(...)` wiring
- Depends on: `apps/api/dependencies/auth.py`, `apps/api/infrastructure/database.py`, `apps/api/models/collection_dto.py`, `apps/api/models/job_dto.py`, `apps/api/services/kra_collection_module.py`, `apps/api/services/job_service.py`
- Used by: `apps/api/main_v2.py`
- Purpose: Authenticate API keys, authorize action-level access, reserve and persist usage events, enforce rate limits, and log requests.
- Location: `apps/api/dependencies/auth.py`, `apps/api/policy/*.py`, `apps/api/middleware/*.py`
- Contains: `require_action()`, `PrincipalAuthenticator`, `PolicyAuthorizer`, `UsageAccountant`, `RateLimitMiddleware`, `RequestLoggingMiddleware`, `PolicyAccountingMiddleware`
- Depends on: `apps/api/config.py`, `apps/api/models/database_models.py`, `apps/api/infrastructure/database.py`, `apps/api/infrastructure/redis_client.py`
- Used by: routers in `apps/api/routers/*.py` and middleware chain in `apps/api/main_v2.py`
- Purpose: Present a small public API to routers instead of exposing service internals directly.
- Location: `apps/api/services/kra_collection_module.py`
- Contains: `CollectionQueries`, `CollectionCommands`, `CollectionJobs`, `KRACollectionModule`
- Depends on: `apps/api/services/collection_service.py`, `apps/api/services/result_collection_service.py`, `apps/api/services/job_service.py`, `apps/api/services/kra_api_service.py`
- Used by: `apps/api/routers/collection_v2.py`
- Purpose: Implement collection, enrichment, result ingestion, job lifecycle management, and KRA endpoint access.
- Location: `apps/api/services/collection_service.py`, `apps/api/services/result_collection_service.py`, `apps/api/services/job_service.py`, `apps/api/services/kra_api_service.py`, `apps/api/services/collection_enrichment.py`, `apps/api/services/collection_preprocessing.py`, `apps/api/services/job_contract.py`
- Contains: business logic, orchestration, SQLAlchemy reads/writes, DTO normalization hooks
- Depends on: `apps/api/models/database_models.py`, `apps/api/adapters/*.py`, `apps/api/infrastructure/*.py`, `apps/api/utils/field_mapping.py`
- Used by: routers, task workers, pipeline stages
- Purpose: Hide DB engine/session setup, migration head checks, Redis cache/state persistence, and low-level KRA transport rules.
- Location: `apps/api/infrastructure/database.py`, `apps/api/infrastructure/migration_manifest.py`, `apps/api/infrastructure/redis_client.py`, `apps/api/infrastructure/background_tasks.py`, `apps/api/infrastructure/kra_api/core.py`, `apps/api/infrastructure/supabase_client.py`
- Contains: SQLAlchemy engine/session factory, migration manifest guard, Redis client setup, in-process task runner, retry/backoff HTTP helpers, optional Supabase client
- Depends on: `apps/api/config.py`
- Used by: runtime layer, services, auth dependencies, health/metrics routers, operational scripts
- Purpose: Separate API DTOs from DB entities.
- Location: `apps/api/models/collection_dto.py`, `apps/api/models/job_dto.py`, `apps/api/models/race_dto.py`, `apps/api/models/database_models.py`
- Contains: Pydantic request/response models and SQLAlchemy ORM entities
- Depends on: `apps/api/infrastructure/database.py` for the ORM base in `apps/api/models/database_models.py`
- Used by: routers, services, policy, tests
- Purpose: Provide a staged pipeline abstraction for collection/preprocessing/enrichment/validation independent of the job runner path.
- Location: `apps/api/pipelines/base.py`, `apps/api/pipelines/data_pipeline.py`, `apps/api/pipelines/stages.py`
- Contains: `Pipeline`, `PipelineBuilder`, `PipelineContext`, stage classes, orchestrator
- Depends on: `apps/api/services/collection_service.py`, `apps/api/services/kra_api_service.py`
- Used by: tests in `apps/api/tests/unit/test_pipeline_base.py`, `apps/api/tests/unit/test_data_pipeline.py`, `apps/api/tests/unit/test_pipeline_stages.py`; not mounted by `apps/api/main_v2.py`
## Data Flow
- Per-request DB state uses `AsyncSession` yielded by `apps/api/infrastructure/database.py`.
- App-wide operational state is stored on `app.state` in `apps/api/main_v2.py` as `db_session_factory` and `runtime`.
- Background task liveness is split between in-memory `_running_tasks` in `apps/api/infrastructure/background_tasks.py` and optional Redis copies of task status.
- Race lifecycle state is persisted in `apps/api/models/database_models.py` across `collection_status`, `enrichment_status`, and `result_status`.
## Key Abstractions
- Purpose: Router-facing facade that separates queries, commands, and async job submission.
- Examples: `apps/api/services/kra_collection_module.py`
- Pattern: facade / application service boundary
- Purpose: Heavy orchestration for race collection, persistence, preprocessing, enrichment, and odds ingestion.
- Examples: `apps/api/services/collection_service.py`
- Pattern: large multi-responsibility domain service
- Purpose: Canonical owner of `Job` records, dispatch routing, status normalization, and cancellation.
- Examples: `apps/api/services/job_service.py`, `apps/api/services/job_contract.py`
- Pattern: service plus normalization contract for legacy/current job vocabulary
- Purpose: Separate endpoint-specific API methods from transport concerns like retries, auth, headers, and cache TTL.
- Examples: `apps/api/services/kra_api_service.py`, `apps/api/infrastructure/kra_api/core.py`
- Pattern: client wrapper over a policy-driven transport helper
- Purpose: Normalize third-party response shapes and internal result projections before business logic uses them.
- Examples: `apps/api/adapters/kra_response_adapter.py`, `apps/api/adapters/race_projection_adapter.py`
- Pattern: translation adapter
- Purpose: Keep health/metrics rendering out of routers and make observability easy to stub in tests.
- Examples: `apps/api/bootstrap/runtime.py`
- Pattern: runtime facade attached to `app.state`
## Entry Points
- Location: `apps/api/main_v2.py`
- Triggers: `uv run uvicorn main_v2:app --reload --port 8000`, `pnpm -w -F @apps/api dev`
- Responsibilities: create FastAPI app, initialize DB/Redis, register middleware and routers, expose root endpoint
- Location: `apps/api/routers/collection_v2.py`, `apps/api/routers/jobs_v2.py`, `apps/api/routers/health.py`, `apps/api/routers/metrics.py`
- Triggers: incoming HTTP requests
- Responsibilities: validate DTOs, invoke auth dependencies, call service/facade layer, translate failures into HTTP responses
- Location: `apps/api/tasks/async_tasks.py`
- Triggers: `JobService._dispatch_task(...)` from `apps/api/services/job_service.py`
- Responsibilities: run collection/preprocess/enrich/full-pipeline jobs with independent DB sessions and job log updates
- Location: `apps/api/scripts/apply_migrations.py`, `apps/api/scripts/check_collection_status_db.py`, `apps/api/scripts/test_db_connection.py`
- Triggers: manual CLI execution
- Responsibilities: schema application, status inspection, connectivity validation
## Key Execution Paths
## Error Handling
- `apps/api/main_v2.py` adds a global exception handler that emits a generated `error_id`.
- `apps/api/services/result_collection_service.py` retries persistence of failure status before giving up.
- `apps/api/middleware/rate_limit.py` and `apps/api/infrastructure/redis_client.py` bypass cache/rate-limit behavior when Redis is unavailable.
- `apps/api/infrastructure/database.py` is strict in non-test startup and permissive in test mode.
## Cross-Cutting Concerns
## Architectural Mismatches
- `apps/api/README.md` still documents `apps/api/routers/race.py` and `apps/api/services/race_service.py`, but those files are not present in the current tree.
- The active mounted router set in `apps/api/main_v2.py` is only `collection_v2`, `jobs_v2`, `health`, and `metrics`.
- `README.md`, `apps/api/README.md`, `apps/api/docs/QUICK_START.md`, and `apps/api/docs/SUPABASE_SETUP.md` refer to `apps/api/.env.template`.
- The tracked example file is `apps/api/.env.example`.
- `apps/api/pipelines/*.py` defines a staged pipeline framework and has dedicated tests.
- Active asynchronous execution flows use `apps/api/services/job_service.py` plus `apps/api/tasks/async_tasks.py` instead of `PipelineOrchestrator`.
- `apps/api/infrastructure/supabase_client.py` exists and is used by scripts such as `apps/api/scripts/test_db_connection.py`.
- Active routers and services use SQLAlchemy sessions from `apps/api/infrastructure/database.py` rather than the Supabase client.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, or `.github/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->

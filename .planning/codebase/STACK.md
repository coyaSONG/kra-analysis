# Technology Stack

**Analysis Date:** 2026-04-05

## Languages

**Primary:**
- Python 3.13 - API runtime and most domain logic live in `apps/api/**/*.py`, with offline evaluation and prompt-improvement workflows in `packages/scripts/**/*.py`.

**Secondary:**
- JavaScript / Node.js - Workspace orchestration and one utility fetcher live in `package.json`, `apps/api/package.json`, and `packages/scripts/evaluation/fetch_and_save_results.js`.
- YAML / JSON / TOML - Build, CI, linting, and dependency configuration live in `turbo.json`, `pnpm-workspace.yaml`, `.github/workflows/ci.yml`, `.github/workflows/codeql.yml`, `apps/api/pyproject.toml`, and `packages/scripts/pyproject.toml`.

## Runtime

**Environment:**
- Python 3.13 is the declared baseline in `.python-version`, `apps/api/pyproject.toml`, `packages/scripts/pyproject.toml`, and `apps/api/Dockerfile`.
- Node.js 22 is the explicit CI/runtime baseline for workspace tooling in `.github/workflows/ci.yml`.

**Package Manager:**
- `pnpm` 9.0.0 manages the monorepo workspace from `package.json`.
- `uv` manages Python dependency resolution and sync for `apps/api` and `packages/scripts` via `uv.lock`, `apps/api/pyproject.toml`, and `packages/scripts/pyproject.toml`.
- Lockfile: present in `pnpm-lock.yaml` and `uv.lock`.

## Frameworks

**Core:**
- FastAPI 0.118.0 - HTTP API framework used by `apps/api/main_v2.py` and the routers under `apps/api/routers/`.
- Uvicorn 0.37.0 - ASGI server used in `apps/api/main_v2.py`, `apps/api/package.json`, and `apps/api/Dockerfile`.
- Pydantic 2.11.9 + `pydantic-settings` 2.11.0 - configuration and DTO validation in `apps/api/config.py` and model modules under `apps/api/models/`.
- SQLAlchemy 2.0.43 + asyncpg 0.30.0 - async database access in `apps/api/infrastructure/database.py` and service modules under `apps/api/services/`.

**Testing:**
- Pytest 8.x with `pytest-asyncio`, `pytest-cov`, and `pytest-timeout` - Python test runner configured in `apps/api/pyproject.toml` and exercised from `apps/api/tests/` and `packages/scripts/evaluation/tests/`.

**Build/Dev:**
- Turbo 2.5.5 - workspace task orchestration defined in `package.json`, `turbo.json`, and `apps/api/turbo.json`.
- Ruff - Python lint/format gate configured in `apps/api/pyproject.toml` and used by `apps/api/scripts/run_quality_ci.sh`.
- Mypy - Python type-checking configured in `apps/api/pyproject.toml`.
- ESLint + Prettier - Node/workspace formatting rules live in `.eslintrc.json`, `.prettierrc`, and `packages/eslint-config/package.json`.
- Docker - containerized API runtime is defined in `apps/api/Dockerfile`.

## Key Dependencies

**Critical:**
- `supabase` 2.20.0 - secondary database/client integration wrapped in `apps/api/infrastructure/supabase_client.py`.
- `redis` 6.4.0 - cache, rate limiting, and background task state in `apps/api/infrastructure/redis_client.py`, `apps/api/middleware/rate_limit.py`, and `apps/api/infrastructure/background_tasks.py`.
- `httpx` 0.28.1 - outbound KRA API client transport in `apps/api/infrastructure/kra_api/core.py` and `apps/api/services/kra_api_service.py`.
- `python-jose` 3.5.0 - optional JWT creation and verification in `apps/api/dependencies/auth.py`.
- `structlog` 25.4.0 - structured JSON logging configured in `apps/api/main_v2.py` and used across the API.

**Infrastructure:**
- `prometheus-client` 0.23.1 - metrics support surfaced by `apps/api/routers/metrics.py` and runtime observability in `apps/api/bootstrap/runtime.py`.
- `pandas` 2.3.2 - collection/enrichment data shaping in `apps/api/services/collection_service.py` and `apps/api/services/collection_enrichment.py`.
- `psycopg2-binary` 2.9.11 - synchronous PostgreSQL access for evaluation scripts in `packages/scripts/shared/db_client.py`.
- `mlflow` 3.9.0 - experiment tracking used by `packages/scripts/evaluation/mlflow_tracker.py` and `packages/scripts/evaluation/evaluate_prompt_v3.py`.
- Local CLI integrations for `claude`, `codex`, and `gemini` are wrapped in `packages/scripts/shared/claude_client.py` and `packages/scripts/shared/llm_client.py`.

## Workspace Layout

**Active workspace packages:**
- Root orchestrator in `package.json` and `turbo.json`.
- API app workspace in `apps/api/package.json` and `apps/api/pyproject.toml`.
- Shared Node config packages in `packages/typescript-config/package.json` and `packages/eslint-config/package.json`.
- Python-heavy script workspace in `packages/scripts/package.json` and `packages/scripts/pyproject.toml`.

**Current shape:**
- No frontend application package is detected under `apps/`; the workspace is backend- and scripting-centric.
- TypeScript is present as shared tooling configuration, not as a substantial application codebase.

## Configuration

**Environment:**
- API settings are centralized in `apps/api/config.py` using `BaseSettings` with `.env` loading.
- Turbo passes shared env through from `turbo.json` and app-specific env through from `apps/api/turbo.json`.
- Environment example files exist at `apps/api/.env.example` and `apps/api/.env.template`; a local `apps/api/.env` file is also present.

**Build:**
- Monorepo task graph: `turbo.json`
- Workspace discovery: `pnpm-workspace.yaml`
- Root Node scripts: `package.json`
- API Python config: `apps/api/pyproject.toml`
- Script Python config: `packages/scripts/pyproject.toml`
- API container image: `apps/api/Dockerfile`
- Node lint/format config: `.eslintrc.json`, `.prettierrc`, `packages/eslint-config/package.json`

## Platform Requirements

**Development:**
- Python 3.13 with `uv` is required to run `apps/api` and `packages/scripts`.
- `pnpm` 9 and Node.js are required for Turbo-driven workspace commands from `package.json`.
- Local PostgreSQL-compatible access and Redis are expected by the API when running outside test mode, based on `apps/api/config.py` and `apps/api/infrastructure/database.py`.

**Production:**
- The deployable artifact detected in-repo is the API container defined by `apps/api/Dockerfile`, which runs `uvicorn main_v2:app`.
- Production assumes a remote PostgreSQL/Supabase database, Redis, and environment-injected secrets as enforced by `apps/api/config.py`.

---

*Stack analysis: 2026-04-05*

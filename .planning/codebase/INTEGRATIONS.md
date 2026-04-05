# External Integrations

**Analysis Date:** 2026-04-05

## APIs & External Services

**Public racing data:**
- KRA public API - primary outbound data source for race, horse, jockey, trainer, track, and result lookups.
  - SDK/Client: `httpx.AsyncClient` built in `apps/api/infrastructure/kra_api/core.py` and used by `apps/api/services/kra_api_service.py`
  - Auth: `KRA_API_KEY`
- KRA result endpoint fallback - Node-based fetch path used by the evaluation tooling when Python-side SSL handling is not preferred.
  - SDK/Client: `node-fetch` in `packages/scripts/evaluation/fetch_and_save_results.js`
  - Auth: `KRA_SERVICE_KEY`

**LLM tooling:**
- Claude CLI - prompt evaluation and prompt-improvement jobs call the locally installed CLI from `packages/scripts/shared/claude_client.py`.
  - SDK/Client: subprocess wrapper in `packages/scripts/shared/llm_client.py`
  - Auth: local CLI session; repo code toggles `DISABLE_INTERLEAVED_THINKING` and `CLAUDE_CODE` in `packages/scripts/shared/claude_client.py` and `packages/scripts/prompt_improvement/recursive_prompt_improvement_v5.py`
- Codex CLI - optional jury/evaluation model invoked from `packages/scripts/shared/llm_client.py`.
  - SDK/Client: subprocess wrapper in `packages/scripts/shared/llm_client.py`
  - Auth: local CLI session
- Gemini CLI - optional jury/evaluation model invoked from `packages/scripts/shared/llm_client.py`.
  - SDK/Client: subprocess wrapper in `packages/scripts/shared/llm_client.py`
  - Auth: local CLI session

## Data Storage

**Databases:**
- PostgreSQL / Supabase Postgres - primary transactional store for races, jobs, API keys, usage events, and related JSON payloads.
  - Connection: `DATABASE_URL`
  - Client: SQLAlchemy async engine in `apps/api/infrastructure/database.py`, ORM models in `apps/api/models/database_models.py`, migrations in `apps/api/migrations/*.sql`
- Supabase REST/Auth-capable client - auxiliary client layer for direct Supabase access when URL/key configuration is present.
  - Connection: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, optional `SUPABASE_SERVICE_ROLE_KEY`
  - Client: `create_client` wrapper in `apps/api/infrastructure/supabase_client.py`
- PostgreSQL synchronous access for offline evaluation scripts.
  - Connection: `DATABASE_URL` loaded from `apps/api/.env` by `packages/scripts/shared/db_client.py`
  - Client: `psycopg2` in `packages/scripts/shared/db_client.py`

**File Storage:**
- Local filesystem only.
  - API runtime writes under `./data`, `./data/cache`, `./logs`, and `./prompts` via `apps/api/config.py` and `apps/api/main_v2.py`
  - Evaluation artifacts live under `data/prompt_evaluation`, `data/cache`, and `mlruns/` from `packages/scripts/evaluation/evaluate_prompt_v3.py` and `packages/scripts/evaluation/mlflow_tracker.py`

**Caching:**
- Redis - shared cache and operational state store.
  - Connection: `REDIS_URL`
  - Client: `redis.asyncio.from_url` in `apps/api/infrastructure/redis_client.py`
  - Uses: KRA response caching via `apps/api/services/kra_api_service.py`, API rate limiting via `apps/api/middleware/rate_limit.py`, and background task state persistence via `apps/api/infrastructure/background_tasks.py`

## Authentication & Identity

**Auth Provider:**
- Custom API key and JWT authentication.
  - Implementation: API keys are accepted from `VALID_API_KEYS` or the `api_keys` database table in `apps/api/dependencies/auth.py`; JWTs are signed with `SECRET_KEY` in the same module
- No external OAuth, SSO, or hosted identity provider is detected.

## Monitoring & Observability

**Error Tracking:**
- None detected as a third-party SaaS integration.
- Structured exception and request logging is implemented locally with `structlog` in `apps/api/main_v2.py` and `apps/api/middleware/logging.py`.

**Logs:**
- JSON logs through `structlog` in `apps/api/main_v2.py`
- Request IDs and masked sensitive fields in `apps/api/middleware/logging.py`
- File log path is configurable through `apps/api/config.py`

**Metrics and experiments:**
- Prometheus-compatible text metrics endpoint at `/metrics` in `apps/api/routers/metrics.py`
- MLflow experiment tracking in `packages/scripts/evaluation/mlflow_tracker.py`

## Background Systems

**Async job execution:**
- In-process asyncio background task runner replaces Celery in `apps/api/infrastructure/background_tasks.py`.
  - Runtime state: in-memory task registry plus Redis persistence
  - Job metadata: `jobs` and `job_logs` tables in `apps/api/models/database_models.py`
- Collection jobs call service modules from `apps/api/tasks/async_tasks.py` and `apps/api/services/job_service.py`.

## CI/CD & Deployment

**Hosting:**
- Containerized API deployment is prepared through `apps/api/Dockerfile`.
- No cloud-specific hosting target, Terraform, Helm, or Kubernetes manifests are detected.

**CI Pipeline:**
- GitHub Actions CI in `.github/workflows/ci.yml`
  - Python job uses `astral-sh/setup-uv@v3`
  - Node job uses `pnpm/action-setup@v4` and `actions/setup-node@v4`
  - Coverage upload uses `codecov/codecov-action@v5`
- Security scanning in `.github/workflows/ci.yml` and `.github/workflows/codeql.yml`
  - Gitleaks via `gitleaks/gitleaks-action@v2`
  - CodeQL via `github/codeql-action/*@v3`

## Environment Configuration

**Required env vars:**
- API runtime core: `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, `ENVIRONMENT`
- API auth and access control: `VALID_API_KEYS`
- KRA ingestion: `KRA_API_KEY`, optional `KRA_API_VERIFY_SSL`
- Supabase: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, optional `SUPABASE_SERVICE_ROLE_KEY`
- Optional runtime toggles: `RATE_LIMIT_ENABLED`, `HOST`, `PORT`, `ALLOWED_ORIGINS`
- Script/evaluation integrations: `KRA_SERVICE_KEY`, optional `MLFLOW_TRACKING_URI`

**Secrets location:**
- Local development secrets are expected in `apps/api/.env` and are loaded by `apps/api/config.py` and `packages/scripts/shared/db_client.py`.
- CI secrets are injected from GitHub Actions secrets in `.github/workflows/ci.yml`.
- Example templates exist in `apps/api/.env.example` and `apps/api/.env.template`.

## Webhooks & Callbacks

**Incoming:**
- None detected. The API exposes REST endpoints in `apps/api/routers/`, but no webhook receiver pattern is configured.

**Outgoing:**
- None detected for webhook-style callbacks.
- Outbound network calls are request/response integrations to the KRA API from `apps/api/services/kra_api_service.py` and `packages/scripts/evaluation/fetch_and_save_results.js`.

---

*Integration audit: 2026-04-05*

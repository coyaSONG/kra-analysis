# Architecture

**Analysis Date:** 2026-04-05

## Pattern Overview

**Overall:** FastAPI modular monolith with explicit HTTP/router, service, infrastructure, and policy layers inside `apps/api`, plus a separate offline experiment workspace in `packages/scripts`.

**Key Characteristics:**
- Runtime composition is centralized in `apps/api/main_v2.py`; the application mounts routers, middleware, DB session factory, and a small runtime facade.
- Request handling is layered as router -> auth dependency/policy -> service facade/service -> infrastructure/model, with `AsyncSession` injected at the router boundary from `apps/api/infrastructure/database.py`.
- Background execution is not an external worker system; `apps/api/infrastructure/background_tasks.py` runs `asyncio.create_task()` jobs in-process and persists best-effort task state in Redis.
- External KRA calls are wrapped twice: transport policy and retry live in `apps/api/infrastructure/kra_api/core.py`, while endpoint-specific methods live in `apps/api/services/kra_api_service.py`.
- Persistence is SQLAlchemy-first. `apps/api/models/database_models.py` is the canonical schema for active API flows, while `apps/api/infrastructure/supabase_client.py` exists but is not in the active HTTP request path.

## Layers

**Runtime Composition:**
- Purpose: Build the FastAPI app, register middleware and routers, manage startup/shutdown.
- Location: `apps/api/main_v2.py`, `apps/api/bootstrap/runtime.py`
- Contains: `create_app()`, lifespan startup/shutdown, `AppRuntime`, `ObservabilityFacade`
- Depends on: `apps/api/config.py`, `apps/api/routers/*.py`, `apps/api/infrastructure/database.py`, `apps/api/infrastructure/redis_client.py`, `apps/api/infrastructure/background_tasks.py`, `apps/api/middleware/*.py`
- Used by: `uvicorn main_v2:app`, tests that call `create_app()` from `apps/api/tests/platform/fixtures.py`

**HTTP Interface Layer:**
- Purpose: Define request/response contracts and map HTTP calls onto services.
- Location: `apps/api/routers/collection_v2.py`, `apps/api/routers/jobs_v2.py`, `apps/api/routers/health.py`, `apps/api/routers/metrics.py`
- Contains: FastAPI route handlers, response shaping, `Depends(...)` wiring
- Depends on: `apps/api/dependencies/auth.py`, `apps/api/infrastructure/database.py`, `apps/api/models/collection_dto.py`, `apps/api/models/job_dto.py`, `apps/api/services/kra_collection_module.py`, `apps/api/services/job_service.py`
- Used by: `apps/api/main_v2.py`

**Policy and Request Guard Layer:**
- Purpose: Authenticate API keys, authorize action-level access, reserve and persist usage events, enforce rate limits, and log requests.
- Location: `apps/api/dependencies/auth.py`, `apps/api/policy/*.py`, `apps/api/middleware/*.py`
- Contains: `require_action()`, `PrincipalAuthenticator`, `PolicyAuthorizer`, `UsageAccountant`, `RateLimitMiddleware`, `RequestLoggingMiddleware`, `PolicyAccountingMiddleware`
- Depends on: `apps/api/config.py`, `apps/api/models/database_models.py`, `apps/api/infrastructure/database.py`, `apps/api/infrastructure/redis_client.py`
- Used by: routers in `apps/api/routers/*.py` and middleware chain in `apps/api/main_v2.py`

**Application Facade Layer:**
- Purpose: Present a small public API to routers instead of exposing service internals directly.
- Location: `apps/api/services/kra_collection_module.py`
- Contains: `CollectionQueries`, `CollectionCommands`, `CollectionJobs`, `KRACollectionModule`
- Depends on: `apps/api/services/collection_service.py`, `apps/api/services/result_collection_service.py`, `apps/api/services/job_service.py`, `apps/api/services/kra_api_service.py`
- Used by: `apps/api/routers/collection_v2.py`

**Domain Service Layer:**
- Purpose: Implement collection, enrichment, result ingestion, job lifecycle management, and KRA endpoint access.
- Location: `apps/api/services/collection_service.py`, `apps/api/services/result_collection_service.py`, `apps/api/services/job_service.py`, `apps/api/services/kra_api_service.py`, `apps/api/services/collection_enrichment.py`, `apps/api/services/collection_preprocessing.py`, `apps/api/services/job_contract.py`
- Contains: business logic, orchestration, SQLAlchemy reads/writes, DTO normalization hooks
- Depends on: `apps/api/models/database_models.py`, `apps/api/adapters/*.py`, `apps/api/infrastructure/*.py`, `apps/api/utils/field_mapping.py`
- Used by: routers, task workers, pipeline stages

**Persistence and External IO Layer:**
- Purpose: Hide DB engine/session setup, migration head checks, Redis cache/state persistence, and low-level KRA transport rules.
- Location: `apps/api/infrastructure/database.py`, `apps/api/infrastructure/migration_manifest.py`, `apps/api/infrastructure/redis_client.py`, `apps/api/infrastructure/background_tasks.py`, `apps/api/infrastructure/kra_api/core.py`, `apps/api/infrastructure/supabase_client.py`
- Contains: SQLAlchemy engine/session factory, migration manifest guard, Redis client setup, in-process task runner, retry/backoff HTTP helpers, optional Supabase client
- Depends on: `apps/api/config.py`
- Used by: runtime layer, services, auth dependencies, health/metrics routers, operational scripts

**Model and Contract Layer:**
- Purpose: Separate API DTOs from DB entities.
- Location: `apps/api/models/collection_dto.py`, `apps/api/models/job_dto.py`, `apps/api/models/race_dto.py`, `apps/api/models/database_models.py`
- Contains: Pydantic request/response models and SQLAlchemy ORM entities
- Depends on: `apps/api/infrastructure/database.py` for the ORM base in `apps/api/models/database_models.py`
- Used by: routers, services, policy, tests

**Secondary Pipeline Layer:**
- Purpose: Provide a staged pipeline abstraction for collection/preprocessing/enrichment/validation independent of the job runner path.
- Location: `apps/api/pipelines/base.py`, `apps/api/pipelines/data_pipeline.py`, `apps/api/pipelines/stages.py`
- Contains: `Pipeline`, `PipelineBuilder`, `PipelineContext`, stage classes, orchestrator
- Depends on: `apps/api/services/collection_service.py`, `apps/api/services/kra_api_service.py`
- Used by: tests in `apps/api/tests/unit/test_pipeline_base.py`, `apps/api/tests/unit/test_data_pipeline.py`, `apps/api/tests/unit/test_pipeline_stages.py`; not mounted by `apps/api/main_v2.py`

## Data Flow

**Synchronous Collection Request (`POST /api/v2/collection/`):**

1. `apps/api/main_v2.py` routes `/api/v2/collection/` to `apps/api/routers/collection_v2.py`.
2. `apps/api/dependencies/auth.py` authenticates `X-API-Key`, authorizes `collection.collect`, and stores a usage reservation on `request.state`.
3. `apps/api/routers/collection_v2.py` creates `BatchCollectInput` and calls `KRACollectionModule.commands.collect_batch(...)` from `apps/api/services/kra_collection_module.py`.
4. `apps/api/services/kra_collection_module.py` lazily builds `KRAAPIService` via `get_kra_api_service()` and creates `CollectionService`.
5. `apps/api/services/collection_service.py` calls multiple KRA endpoints through `apps/api/services/kra_api_service.py`, normalizes responses with `apps/api/adapters/kra_response_adapter.py`, enriches horse details, and persists `Race` rows through `AsyncSession`.
6. Middleware in `apps/api/middleware/policy_accounting.py` writes a `UsageEvent` through `apps/api/policy/accounting.py` after the response completes.

**Asynchronous Collection Request (`POST /api/v2/collection/async`):**

1. `apps/api/routers/collection_v2.py` authorizes `collection.collect_async` and calls `KRACollectionModule.jobs.submit_batch_collect(...)`.
2. `apps/api/services/kra_collection_module.py` delegates to `JobService.create_job(...)` and `JobService.start_job(...)` in `apps/api/services/job_service.py`.
3. `apps/api/services/job_service.py` stores a `Job` row, normalizes shadow fields with `apps/api/services/job_contract.py`, and dispatches work through `submit_task(...)` from `apps/api/infrastructure/background_tasks.py`.
4. `apps/api/infrastructure/background_tasks.py` creates an in-memory `asyncio.Task`, persists state in Redis when available, and invokes `apps/api/tasks/async_tasks.py`.
5. `apps/api/tasks/async_tasks.py` opens its own DB session from `async_session_maker`, runs `CollectionService`, and updates `Job`/`JobLog` rows.
6. `apps/api/routers/jobs_v2.py` exposes status and cancellation by reading `Job` rows and consulting live task state from `get_task_status(...)` or `cancel_task(...)`.

**Result Collection Request (`POST /api/v2/collection/result`):**

1. `apps/api/routers/collection_v2.py` authorizes `collection.result.collect`.
2. `apps/api/services/kra_collection_module.py` routes the request to `ResultCollectionService.collect_result(...)`.
3. `apps/api/services/result_collection_service.py` loads the `Race` row, fetches result payloads from `KRAAPIService`, normalizes top-3 output with `apps/api/adapters/race_projection_adapter.py`, updates `Race.result_data`, then optionally upserts `RaceOdds`.
4. On failure, `ResultCollectionService` marks `Race.result_status` as failed through `_mark_result_failure_with_retry(...)`.

**Health and Metrics Path:**

1. `apps/api/routers/health.py` and `apps/api/routers/metrics.py` depend on `get_runtime(...)` from `apps/api/bootstrap/runtime.py`.
2. DB reachability comes from `check_database_connection(...)` in `apps/api/infrastructure/database.py`.
3. Redis reachability comes from `check_redis_connection()` or `get_redis()` in `apps/api/infrastructure/redis_client.py`.
4. Background-task counts and request totals come from `apps/api/infrastructure/background_tasks.py` and `apps/api/middleware/logging.py`.

**State Management:**
- Per-request DB state uses `AsyncSession` yielded by `apps/api/infrastructure/database.py`.
- App-wide operational state is stored on `app.state` in `apps/api/main_v2.py` as `db_session_factory` and `runtime`.
- Background task liveness is split between in-memory `_running_tasks` in `apps/api/infrastructure/background_tasks.py` and optional Redis copies of task status.
- Race lifecycle state is persisted in `apps/api/models/database_models.py` across `collection_status`, `enrichment_status`, and `result_status`.

## Key Abstractions

**`KRACollectionModule`:**
- Purpose: Router-facing facade that separates queries, commands, and async job submission.
- Examples: `apps/api/services/kra_collection_module.py`
- Pattern: facade / application service boundary

**`CollectionService`:**
- Purpose: Heavy orchestration for race collection, persistence, preprocessing, enrichment, and odds ingestion.
- Examples: `apps/api/services/collection_service.py`
- Pattern: large multi-responsibility domain service

**`JobService`:**
- Purpose: Canonical owner of `Job` records, dispatch routing, status normalization, and cancellation.
- Examples: `apps/api/services/job_service.py`, `apps/api/services/job_contract.py`
- Pattern: service plus normalization contract for legacy/current job vocabulary

**`KRAAPIService` + `KRARequestPolicy`:**
- Purpose: Separate endpoint-specific API methods from transport concerns like retries, auth, headers, and cache TTL.
- Examples: `apps/api/services/kra_api_service.py`, `apps/api/infrastructure/kra_api/core.py`
- Pattern: client wrapper over a policy-driven transport helper

**Adapters:**
- Purpose: Normalize third-party response shapes and internal result projections before business logic uses them.
- Examples: `apps/api/adapters/kra_response_adapter.py`, `apps/api/adapters/race_projection_adapter.py`
- Pattern: translation adapter

**`AppRuntime` / `ObservabilityFacade`:**
- Purpose: Keep health/metrics rendering out of routers and make observability easy to stub in tests.
- Examples: `apps/api/bootstrap/runtime.py`
- Pattern: runtime facade attached to `app.state`

## Entry Points

**HTTP App:**
- Location: `apps/api/main_v2.py`
- Triggers: `uv run uvicorn main_v2:app --reload --port 8000`, `pnpm -w -F @apps/api dev`
- Responsibilities: create FastAPI app, initialize DB/Redis, register middleware and routers, expose root endpoint

**Router Surface:**
- Location: `apps/api/routers/collection_v2.py`, `apps/api/routers/jobs_v2.py`, `apps/api/routers/health.py`, `apps/api/routers/metrics.py`
- Triggers: incoming HTTP requests
- Responsibilities: validate DTOs, invoke auth dependencies, call service/facade layer, translate failures into HTTP responses

**Background Worker Functions:**
- Location: `apps/api/tasks/async_tasks.py`
- Triggers: `JobService._dispatch_task(...)` from `apps/api/services/job_service.py`
- Responsibilities: run collection/preprocess/enrich/full-pipeline jobs with independent DB sessions and job log updates

**Operational Scripts:**
- Location: `apps/api/scripts/apply_migrations.py`, `apps/api/scripts/check_collection_status_db.py`, `apps/api/scripts/test_db_connection.py`
- Triggers: manual CLI execution
- Responsibilities: schema application, status inspection, connectivity validation

## Key Execution Paths

**Startup Path:**
1. `apps/api/main_v2.py` creates directories from `settings`.
2. `apps/api/infrastructure/database.py:init_db()` creates tables in test/sqlite mode or enforces `apps/api/infrastructure/migration_manifest.py` in non-test mode.
3. `apps/api/infrastructure/redis_client.py:init_redis()` initializes Redis on a fail-open basis.
4. `apps/api/main_v2.py` stores `async_session_maker` and `AppRuntime` on `app.state`.

**Async Job Cancellation Path:**
1. `apps/api/routers/jobs_v2.py:cancel_job(...)` authorizes `jobs.cancel`.
2. `apps/api/services/job_service.py:cancel_job(...)` checks DB ownership/state.
3. `apps/api/infrastructure/background_tasks.py:cancel_task(...)` cancels the live `asyncio.Task`.
4. `apps/api/services/job_service.py` persists `Job.status = "cancelled"` and adds a `JobLog`.

**Migration Guard Path:**
1. `apps/api/infrastructure/database.py:require_migration_manifest()` loads the canonical migration list from `apps/api/infrastructure/migration_manifest.py`.
2. Applied migration names are read from `schema_migrations`.
3. App startup fails if missing or unexpected migration names are found.

## Error Handling

**Strategy:** API handlers use local `try/except` blocks for domain-specific failures and a global exception handler in `apps/api/main_v2.py` for uncaught exceptions; infrastructure layers prefer fail-open behavior for Redis-dependent features.

**Patterns:**
- `apps/api/main_v2.py` adds a global exception handler that emits a generated `error_id`.
- `apps/api/services/result_collection_service.py` retries persistence of failure status before giving up.
- `apps/api/middleware/rate_limit.py` and `apps/api/infrastructure/redis_client.py` bypass cache/rate-limit behavior when Redis is unavailable.
- `apps/api/infrastructure/database.py` is strict in non-test startup and permissive in test mode.

## Cross-Cutting Concerns

**Logging:** `structlog` is configured in `apps/api/main_v2.py`; request logging and request counts live in `apps/api/middleware/logging.py`.

**Validation:** HTTP payload validation uses Pydantic models in `apps/api/models/collection_dto.py` and `apps/api/models/job_dto.py`; DB migration validation is enforced by `apps/api/infrastructure/database.py`.

**Authentication:** API key auth and action-level authorization are centralized in `apps/api/dependencies/auth.py` and `apps/api/policy/*.py`.

**Observability:** `apps/api/bootstrap/runtime.py` renders health snapshots and Prometheus text metrics from runtime state.

## Architectural Mismatches

**Documentation references missing legacy modules:**
- `apps/api/README.md` still documents `apps/api/routers/race.py` and `apps/api/services/race_service.py`, but those files are not present in the current tree.
- The active mounted router set in `apps/api/main_v2.py` is only `collection_v2`, `jobs_v2`, `health`, and `metrics`.

**Environment-template docs do not match tracked files:**
- `README.md`, `apps/api/README.md`, `apps/api/docs/QUICK_START.md`, and `apps/api/docs/SUPABASE_SETUP.md` refer to `apps/api/.env.template`.
- The tracked example file is `apps/api/.env.example`.

**Pipeline abstractions are secondary, not primary runtime architecture:**
- `apps/api/pipelines/*.py` defines a staged pipeline framework and has dedicated tests.
- Active asynchronous execution flows use `apps/api/services/job_service.py` plus `apps/api/tasks/async_tasks.py` instead of `PipelineOrchestrator`.

**Supabase client is present but outside the active request path:**
- `apps/api/infrastructure/supabase_client.py` exists and is used by scripts such as `apps/api/scripts/test_db_connection.py`.
- Active routers and services use SQLAlchemy sessions from `apps/api/infrastructure/database.py` rather than the Supabase client.

---

*Architecture analysis: 2026-04-05*

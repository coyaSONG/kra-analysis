# Codebase Structure

**Analysis Date:** 2026-04-05

## Directory Layout

```text
kra-analysis/
├── apps/
│   └── api/                   # Active FastAPI runtime and operational scripts
├── packages/
│   ├── eslint-config/         # Shared ESLint config package
│   ├── scripts/               # Offline evaluation, prompt improvement, research scripts
│   ├── typescript-config/     # Shared TS config package
│   ├── prompts/               # Prompt assets, not a packaged workspace module
│   └── data/                  # Evaluation artifacts and snapshots, not runtime code
├── docs/                      # Product, remediation, and architecture docs
├── data/                      # Root-level project data assets
├── examples/                  # Sample payloads and examples
├── .planning/                 # Planning artifacts, including generated codebase maps
├── package.json               # Root Turbo/pnpm orchestration
├── pyproject.toml             # Root Python workspace/tooling configuration
├── pnpm-workspace.yaml        # Workspace membership
└── turbo.json                 # Task graph and cache configuration
```

## Directory Purposes

**`apps/api/`:**
- Purpose: Primary runtime application.
- Contains: FastAPI app, routers, services, middleware, auth/policy, infrastructure, migrations, tests, scripts.
- Key files: `apps/api/main_v2.py`, `apps/api/config.py`, `apps/api/infrastructure/database.py`, `apps/api/services/collection_service.py`

**`apps/api/routers/`:**
- Purpose: HTTP endpoint layer only.
- Contains: Route handlers for collection, jobs, health, and metrics.
- Key files: `apps/api/routers/collection_v2.py`, `apps/api/routers/jobs_v2.py`, `apps/api/routers/health.py`, `apps/api/routers/metrics.py`

**`apps/api/services/`:**
- Purpose: Application and domain orchestration.
- Contains: collection, job, result, enrichment, preprocessing, diagnostics, and external API service logic.
- Key files: `apps/api/services/kra_collection_module.py`, `apps/api/services/collection_service.py`, `apps/api/services/job_service.py`, `apps/api/services/result_collection_service.py`, `apps/api/services/kra_api_service.py`

**`apps/api/infrastructure/`:**
- Purpose: Concrete IO adapters and platform setup.
- Contains: SQLAlchemy setup, migration manifest, Redis client, background task runner, KRA transport primitives, optional Supabase client.
- Key files: `apps/api/infrastructure/database.py`, `apps/api/infrastructure/background_tasks.py`, `apps/api/infrastructure/redis_client.py`, `apps/api/infrastructure/kra_api/core.py`, `apps/api/infrastructure/migration_manifest.py`

**`apps/api/models/`:**
- Purpose: Request/response DTOs and ORM models.
- Contains: Pydantic models and SQLAlchemy entities.
- Key files: `apps/api/models/collection_dto.py`, `apps/api/models/job_dto.py`, `apps/api/models/database_models.py`

**`apps/api/dependencies/` and `apps/api/policy/`:**
- Purpose: Authentication, authorization, and usage accounting seams.
- Contains: FastAPI dependencies, principal types, action policy, accountant logic.
- Key files: `apps/api/dependencies/auth.py`, `apps/api/policy/authentication.py`, `apps/api/policy/authorization.py`, `apps/api/policy/accounting.py`, `apps/api/policy/principal.py`

**`apps/api/middleware/`:**
- Purpose: Request logging, rate limiting, and post-response usage accounting.
- Contains: middleware classes and request counters.
- Key files: `apps/api/middleware/logging.py`, `apps/api/middleware/rate_limit.py`, `apps/api/middleware/policy_accounting.py`

**`apps/api/tasks/`:**
- Purpose: Async job worker functions executed by the in-process task runner.
- Contains: task entrypoints for collection, preprocess, enrich, and full-pipeline work.
- Key files: `apps/api/tasks/async_tasks.py`

**`apps/api/pipelines/`:**
- Purpose: Standalone staged pipeline abstraction.
- Contains: pipeline primitives, stage implementations, orchestration helpers.
- Key files: `apps/api/pipelines/base.py`, `apps/api/pipelines/data_pipeline.py`, `apps/api/pipelines/stages.py`

**`apps/api/adapters/`:**
- Purpose: Normalize third-party and legacy result shapes.
- Contains: KRA response and race result projection adapters.
- Key files: `apps/api/adapters/kra_response_adapter.py`, `apps/api/adapters/race_projection_adapter.py`

**`apps/api/utils/`:**
- Purpose: Shared low-level helpers that do not belong in infrastructure.
- Contains: field mapping utilities for KRA payload normalization.
- Key files: `apps/api/utils/field_mapping.py`

**`apps/api/migrations/`:**
- Purpose: SQL schema source of truth for non-test startup.
- Contains: numbered SQL files; the active chain is defined separately in `apps/api/infrastructure/migration_manifest.py`.
- Key files: `apps/api/migrations/001_unified_schema.sql`, `apps/api/migrations/005_add_usage_events.sql`

**`apps/api/scripts/`:**
- Purpose: Operational maintenance and verification scripts.
- Contains: migration application, DB checks, batch backfill, quality runner.
- Key files: `apps/api/scripts/apply_migrations.py`, `apps/api/scripts/check_collection_status_db.py`, `apps/api/scripts/test_db_connection.py`, `apps/api/scripts/run_quality_ci.sh`

**`apps/api/tests/`:**
- Purpose: Runtime-facing regression coverage.
- Contains: unit, integration, platform fakes/contracts, common fixtures.
- Key files: `apps/api/tests/conftest.py`, `apps/api/tests/platform/fixtures.py`, `apps/api/tests/integration/test_api_endpoints.py`

**`packages/scripts/`:**
- Purpose: Offline experimentation, prompt evaluation, and research tooling.
- Contains: Python scripts, tests, and shared helpers for evaluation and prompt improvement.
- Key files: `packages/scripts/package.json`, `packages/scripts/pyproject.toml`, `packages/scripts/evaluation/evaluate_prompt_v3.py`, `packages/scripts/prompt_improvement/recursive_prompt_improvement_v5.py`

**`packages/eslint-config/` and `packages/typescript-config/`:**
- Purpose: Workspace-level TypeScript and lint config packages.
- Contains: config JSON/JS only.
- Key files: `packages/eslint-config/package.json`, `packages/eslint-config/node.js`, `packages/typescript-config/base.json`

**`packages/prompts/` and `packages/data/`:**
- Purpose: Asset storage under the `packages/` root, not active code packages.
- Contains: markdown prompt templates and generated evaluation data.
- Key files: `packages/prompts/base-prompt-v1.5.md`, `packages/data/prompt_evaluation/evaluation_v1.5_20251207_151818.json`

## Key File Locations

**Entry Points:**
- `apps/api/main_v2.py`: active FastAPI application factory and runtime composition root
- `apps/api/tasks/async_tasks.py`: active worker function module for background jobs
- `apps/api/scripts/apply_migrations.py`: CLI migration entrypoint
- `packages/scripts/evaluation/evaluate_prompt_v3.py`: offline evaluation entrypoint
- `packages/scripts/prompt_improvement/recursive_prompt_improvement_v5.py`: offline prompt-improvement entrypoint

**Configuration:**
- `package.json`: root Turbo task aliases
- `pnpm-workspace.yaml`: workspace membership
- `turbo.json`: task graph, env passthrough, and test inputs/outputs
- `pyproject.toml`: root Python workspace and Ruff settings
- `apps/api/pyproject.toml`: API dependencies and pytest config
- `apps/api/config.py`: runtime settings and environment loading

**Core Logic:**
- `apps/api/services/kra_collection_module.py`: router-facing collection facade
- `apps/api/services/collection_service.py`: collection/preprocess/enrich/odds orchestration
- `apps/api/services/job_service.py`: job lifecycle and dispatch
- `apps/api/services/result_collection_service.py`: result/odds persistence path
- `apps/api/services/kra_api_service.py`: KRA endpoint methods and cache wiring

**Persistence:**
- `apps/api/models/database_models.py`: canonical ORM entities
- `apps/api/infrastructure/database.py`: engine/session lifecycle and migration guard
- `apps/api/infrastructure/migration_manifest.py`: active SQL migration chain

**Testing:**
- `apps/api/tests/unit/`: unit-heavy runtime tests
- `apps/api/tests/integration/`: HTTP and flow integration tests
- `apps/api/tests/platform/`: fake runner/redis contracts and app harness support
- `packages/scripts/tests/`: offline script tests
- `packages/scripts/evaluation/tests/`: evaluation-specific tests

## Ownership Boundaries

**HTTP boundary stays in `apps/api/routers/`:**
- Keep request parsing, `Depends(...)`, and HTTPException translation in router files.
- Do not move DB writes or KRA API orchestration into `apps/api/routers/*.py`.

**Policy boundary stays in `apps/api/dependencies/` and `apps/api/policy/`:**
- Add new API actions to `apps/api/policy/authorization.py`.
- Keep principal creation and usage accounting out of service modules.

**Service boundary stays in `apps/api/services/`:**
- New runtime business logic belongs here.
- `apps/api/services/kra_collection_module.py` is the right place for new router-facing collection commands or queries.
- `apps/api/services/job_service.py` owns job creation, status normalization, and dispatch vocabulary.

**Infrastructure boundary stays in `apps/api/infrastructure/`:**
- DB engines, Redis clients, task runners, and third-party transport policies belong here.
- Avoid importing HTTP-layer objects into `apps/api/infrastructure/*.py`.

**Offline experimentation boundary stays in `packages/scripts/`:**
- Evaluation and prompt-improvement code belongs in `packages/scripts/`.
- Do not couple `apps/api` runtime imports to `packages/scripts/`; current runtime code does not depend on it.

## Naming Conventions

**Files:**
- Python modules use `snake_case.py`: `apps/api/services/collection_service.py`
- Active HTTP route modules use `_v2` suffix when versioned: `apps/api/routers/collection_v2.py`, `apps/api/routers/jobs_v2.py`
- DTO modules use `*_dto.py`: `apps/api/models/collection_dto.py`, `apps/api/models/job_dto.py`
- Adapter modules use `*_adapter.py`: `apps/api/adapters/kra_response_adapter.py`
- SQL migrations use numeric prefixes: `apps/api/migrations/001_unified_schema.sql`

**Directories:**
- Runtime directories are role-based: `routers`, `services`, `infrastructure`, `models`, `middleware`, `policy`
- Test directories are scope-based: `apps/api/tests/unit`, `apps/api/tests/integration`, `apps/api/tests/platform`
- Offline script directories are workflow-based: `packages/scripts/evaluation`, `packages/scripts/prompt_improvement`, `packages/scripts/autoresearch`

## Where to Add New Code

**New API endpoint:**
- Route handler: `apps/api/routers/`
- Request/response DTO: `apps/api/models/`
- Auth action: `apps/api/policy/authorization.py`
- Business logic: `apps/api/services/`
- Tests: `apps/api/tests/unit/` and `apps/api/tests/integration/`

**New background job type:**
- Dispatch vocabulary: `apps/api/services/job_contract.py`
- Dispatch logic: `apps/api/services/job_service.py`
- Worker function: `apps/api/tasks/async_tasks.py`
- Job API coverage: `apps/api/tests/unit/test_job_service.py` and router tests under `apps/api/tests/integration/`

**New DB-backed feature:**
- ORM model: `apps/api/models/database_models.py`
- Migration SQL: `apps/api/migrations/`
- Migration manifest if active: `apps/api/infrastructure/migration_manifest.py`
- Service logic: `apps/api/services/`

**New external API or platform client:**
- Low-level transport/policy: `apps/api/infrastructure/`
- Endpoint-specific wrapper: `apps/api/services/`
- Response-shape normalization: `apps/api/adapters/`

**New offline experiment:**
- Script module: `packages/scripts/evaluation/`, `packages/scripts/prompt_improvement/`, or `packages/scripts/autoresearch/`
- Shared helper: `packages/scripts/shared/`
- Tests: adjacent test directory under `packages/scripts/`

## Special Directories

**Generated and cache directories:**
- `apps/api/htmlcov/`, `htmlcov/`, `.mypy_cache/`, `apps/api/.mypy_cache/`, `apps/api/.ruff_cache/`, `apps/api/.pytest_cache/`
- Purpose: generated coverage and tool caches
- Generated: Yes
- Committed: Mixed; these directories are present in the tree and should not be treated as source locations

**Runtime data directories:**
- `apps/api/data/`, `apps/api/data/cache/`, `apps/api/logs/`
- Purpose: local runtime artifacts created/used by the API
- Generated: Yes
- Committed: Partially; the directories exist, but planning and feature work should not store source code here

**Planning directory:**
- `.planning/codebase/`
- Purpose: generated repository maps for future planning and execution
- Generated: Yes
- Committed: Intended for planning artifacts

## Structure Mismatches

**README package map is ahead of the actual tree:**
- `README.md` still lists `packages/shared-types/`, but the current workspace code packages are `packages/eslint-config/`, `packages/scripts/`, and `packages/typescript-config/`.
- `packages/prompts/` and `packages/data/` exist under `packages/`, but they are content directories rather than package manifests.

**Environment-example path is inconsistent across docs:**
- `README.md` and `apps/api/README.md` instruct copying `apps/api/.env.template`.
- The tracked example file is `apps/api/.env.example`.

**API README lists missing legacy files as if they are present:**
- `apps/api/README.md` shows `apps/api/routers/race.py` and `apps/api/services/race_service.py` in the structure block.
- Those files are absent; active routing is defined only by the imports in `apps/api/main_v2.py`.

**`packages/scripts/README.md` overstates the current script tree:**
- The document references `packages/scripts/ml/`, `packages/scripts/archive/`, `packages/scripts/batch_collect_2025.py`, and `packages/scripts/hybrid_predictor.py`.
- The current tree contains `packages/scripts/evaluation/`, `packages/scripts/prompt_improvement/`, `packages/scripts/autoresearch/`, `packages/scripts/shared/`, and `packages/scripts/feature_engineering.py`, but not those referenced paths.

**Pipeline location is real code but not a mounted runtime entrypoint:**
- `apps/api/pipelines/` is a maintained library with tests.
- Runtime HTTP and async-job paths are still driven by `apps/api/routers/*.py`, `apps/api/services/*.py`, and `apps/api/tasks/async_tasks.py`.

---

*Structure analysis: 2026-04-05*

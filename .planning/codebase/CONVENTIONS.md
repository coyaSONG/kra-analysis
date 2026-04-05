# Coding Conventions

**Analysis Date:** 2026-04-05

## Evidence Sources

**Documented conventions:**
- Repository guidance in `AGENTS.md`
- JavaScript formatting rules in `.eslintrc.json` and `.prettierrc`
- Root Python tooling in `pyproject.toml`
- API-specific Python, mypy, pytest, and coverage settings in `apps/api/pyproject.toml`, `apps/api/pytest.ini`, and `apps/api/.coveragerc`
- Script-package Python tooling in `packages/scripts/pyproject.toml`
- Environment setup template in `apps/api/.env.template`

**Conventions inferred from code:**
- FastAPI entrypoint and middleware wiring in `apps/api/main_v2.py`
- Settings and env loading in `apps/api/config.py`
- Router/service/module boundaries in `apps/api/routers/collection_v2.py`, `apps/api/services/collection_service.py`, `apps/api/services/job_service.py`, and `apps/api/bootstrap/runtime.py`
- Data-model patterns in `apps/api/models/collection_dto.py` and `apps/api/models/database_models.py`
- Authentication and error conventions in `apps/api/dependencies/auth.py`
- Script-package style in `packages/scripts/shared/llm_client.py`, `packages/scripts/shared/db_client.py`, `packages/scripts/evaluation/data_loading.py`, and `packages/scripts/prompt_improvement/jury_prompt_improver.py`

## Naming Patterns

**Documented:**
- Python functions and variables use `snake_case`; classes use `PascalCase` per `AGENTS.md`.
- TypeScript, where present, should use `camelCase` for variables/functions and `PascalCase` for types/classes per `AGENTS.md`.

**Inferred from code:**
- API module filenames use `snake_case` and describe their layer role: `apps/api/services/collection_service.py`, `apps/api/routers/jobs_v2.py`, `apps/api/middleware/rate_limit.py`, `apps/api/dependencies/auth.py`.
- Request/response DTO classes are named by domain plus role: `CollectionRequest`, `CollectionResponse`, `ResultCollectionRequest` in `apps/api/models/collection_dto.py`; `JobListResponse` and related DTOs in `apps/api/models/job_dto.py`.
- Persistence models use singular `PascalCase` class names and plural table names: `Race`, `Job`, `Prediction`, `APIKey` in `apps/api/models/database_models.py`.
- Compatibility fields are labeled explicitly with legacy-oriented names instead of silent reuse: `job_kind_v2`, `lifecycle_state_v2` in `apps/api/models/database_models.py`, and compatibility properties like `race_date` and `race_no` in `apps/api/models/database_models.py`.
- Service-layer helper aliases use descriptive suffixes to disambiguate imports: `analyze_weather_impact_helper`, `preprocess_data_helper` in `apps/api/services/collection_service.py`.
- Script-package modules also use `snake_case`, but import path setup is often manual via `sys.path.insert(...)` in `packages/scripts/evaluation/evaluate_prompt_v3.py`, `packages/scripts/evaluation/predict_only_test.py`, and `packages/scripts/prompt_improvement/jury_prompt_improver.py`.

## Code Style

**Documented:**
- JavaScript formatting is 2-space indent, single quotes, semicolons, trailing commas on multiline structures, max length 120, and ESM modules via `.eslintrc.json` and `.prettierrc`.
- Python uses Ruff with line length 88 and target `py313` in `pyproject.toml` and `apps/api/pyproject.toml`.
- Ruff lint sets include `E`, `W`, `F`, `I`, `B`, `C4`, and `UP` in both `pyproject.toml` and `apps/api/pyproject.toml`.
- Mypy is configured only for the API package in `apps/api/pyproject.toml`, and the settings are intentionally permissive: `disallow_untyped_defs = false`, `ignore_missing_imports = true`.

**Inferred from code:**
- Python files commonly begin with a module docstring, even for small modules, for example `apps/api/main_v2.py`, `apps/api/config.py`, `apps/api/middleware/logging.py`, and `packages/scripts/shared/llm_client.py`.
- Import grouping is consistent: stdlib first, third-party second, local application imports last. See `apps/api/services/collection_service.py`, `apps/api/dependencies/auth.py`, and `packages/scripts/shared/db_client.py`.
- Newer modules prefer modern typing syntax such as `list[str]`, `dict[str, Any]`, `str | None`, and Python 3.12 type alias syntax (`type DispatchHandler = ...`) as seen in `apps/api/services/job_service.py`.
- Value objects and internal contracts increasingly use `@dataclass`, often with `frozen=True` and `slots=True`, for example `apps/api/policy/principal.py`, `apps/api/services/kra_collection_module.py`, and `apps/api/infrastructure/kra_api/core.py`.
- Older Pydantic request models still use v1-style `@validator` and `class Config` patterns in `apps/api/models/collection_dto.py`, even though the runtime depends on Pydantic v2 in `apps/api/pyproject.toml`.

## Module and Layer Patterns

**Documented:**
- Domain logic should stay in `services/`; HTTP and I/O should stay in the API layer per `AGENTS.md`.

**Inferred from code:**
- FastAPI setup is centralized in `apps/api/main_v2.py`; route modules are mounted there and should not duplicate app construction elsewhere.
- HTTP boundary code lives in `apps/api/routers/*.py` and stays relatively thin. Routers mostly validate inputs, acquire dependencies, translate exceptions to `HTTPException`, and delegate to services or workflow modules, as in `apps/api/routers/collection_v2.py` and `apps/api/routers/jobs_v2.py`.
- Business logic lives under `apps/api/services/*.py`; these modules coordinate adapters, infrastructure, database sessions, and policy code. `apps/api/services/collection_service.py` and `apps/api/services/job_service.py` are canonical examples.
- Shared infrastructure is isolated under `apps/api/infrastructure/*.py` for DB, Redis, KRA API transport, and background task plumbing.
- Request-scoped and app-scoped cross-cutting concerns are separated into `apps/api/middleware/*.py` and `apps/api/bootstrap/runtime.py`.
- Script-package code under `packages/scripts` is flatter and less layered than the API. It often favors direct imports and command-oriented modules over explicit service boundaries, as seen in `packages/scripts/evaluation/data_loading.py` and `packages/scripts/prompt_improvement/jury_prompt_improver.py`.

## Typing and Data-Model Patterns

**Documented:**
- Use Python 3.13+ across the repo per `pyproject.toml`, `apps/api/pyproject.toml`, and `packages/scripts/pyproject.toml`.

**Inferred from code:**
- FastAPI request/response payloads are modeled with Pydantic `BaseModel` plus rich `Field(...)` metadata for schema descriptions in `apps/api/models/collection_dto.py` and `apps/api/models/job_dto.py`.
- SQLAlchemy models use typed declarative mappings with `Mapped[...]` and `mapped_column(...)` rather than untyped legacy ORM style. See `apps/api/models/database_models.py`.
- The code distinguishes external KRA payload shape from internal shape. External API fields stay camelCase in DTOs like `HorseData.chulNo` and `RaceInfo.rcDate` in `apps/api/models/collection_dto.py`, while internal processing and persistence use `snake_case` fields like `race_number`, `result_status`, and `created_by` in `apps/api/models/database_models.py`.
- Field-shape translation is explicit rather than implicit. `convert_api_to_internal` in `apps/api/utils/field_mapping.py` and adapter logic in `apps/api/adapters/kra_response_adapter.py` are the expected bridge points.
- Backward compatibility is preserved inside models rather than through duplicated tables or DTOs. Examples include `Race.race_date`, `Race.race_no`, and `Race.status` compatibility properties in `apps/api/models/database_models.py`.
- Script-package code frequently uses small dataclasses for in-memory contracts, such as `LLMResponse` in `packages/scripts/shared/llm_client.py` and `RaceEvaluationDataLoader` in `packages/scripts/evaluation/data_loading.py`.

## Configuration and Environment Handling

**Documented:**
- Real secrets belong in `.env` files and must not be committed, with `apps/api/.env.template` as the setup template per `AGENTS.md`.
- Turbo passes through `KRA_*`, `SUPABASE_*`, `REDIS_*`, `DATABASE_URL`, `SECRET_KEY`, `CELERY_*`, and `PG*` environment variables via `turbo.json`.

**Inferred from code:**
- API configuration is centralized in `apps/api/config.py` via `Settings(BaseSettings)`. Modules usually import the global singleton `settings` rather than instantiating settings ad hoc.
- The API settings object uses env aliases for some fields, for example `SUPABASE_ANON_KEY` and `SUPABASE_SERVICE_ROLE_KEY` in `apps/api/config.py`.
- Production guardrails are enforced during settings load, not deferred until first use. `apps/api/config.py` raises immediately for unsafe defaults such as the dev `SECRET_KEY`, missing `VALID_API_KEYS`, insecure `DATABASE_URL`, or placeholder Supabase values.
- Tests mutate the global config singleton instead of rebuilding the app with isolated settings providers. `_apply_test_settings_to_global()` in `apps/api/tests/platform/fixtures.py` is the established pattern.
- Script-package code does not reuse `Settings(BaseSettings)`. `packages/scripts/shared/db_client.py` reads `apps/api/.env` directly with `dotenv_values`, then rewrites `postgresql+asyncpg://` URLs for `psycopg2`.
- Because script modules often load env state directly and patch `sys.path`, future code in `packages/scripts` should follow the existing explicit-path style unless the package layout is first normalized.

## Error Handling Conventions

**Inferred from code:**
- Router boundaries usually catch broad exceptions, log them, and convert them to `HTTPException`. Examples: `apps/api/routers/collection_v2.py` and `apps/api/routers/jobs_v2.py`.
- Service boundaries wrap DB mutations in `try/except`, log structured error details, and `rollback()` before re-raising. `apps/api/services/job_service.py` is the clearest reference.
- Optional dependencies are often fail-open instead of hard-failing the request path. Redis initialization in `apps/api/main_v2.py`, cache access in `apps/api/infrastructure/redis_client.py`, and rate limiting in `apps/api/middleware/rate_limit.py` all degrade gracefully when Redis is unavailable.
- Global exception handling in `apps/api/main_v2.py` generates an `error_id` and returns a generic 500 payload instead of leaking stack traces.
- The API distinguishes user-visible validation errors from operational backend errors. `apps/api/dependencies/auth.py` raises `401` for missing/invalid API keys, `429` for quota exhaustion, and `503` when the auth backend is unavailable.
- Script-package modules are less uniform: some return `None` and print errors (`packages/scripts/evaluation/data_loading.py`), while others rely on stdlib logging (`packages/scripts/prompt_improvement/jury_prompt_improver.py`). New script code should match the local module style rather than importing API patterns blindly.

## Logging Conventions

**Documented:**
- Logging is configurable via env-backed settings like `log_level`, `log_format`, and `log_file` in `apps/api/config.py`.

**Inferred from code:**
- The API standard is `structlog`. Most runtime modules define `logger = structlog.get_logger()` at module scope, for example `apps/api/main_v2.py`, `apps/api/dependencies/auth.py`, `apps/api/services/collection_service.py`, and `apps/api/infrastructure/database.py`.
- Structured key-value logging is preferred over interpolated strings when context matters. Good examples: `logger.error("Unhandled exception", error_id=..., path=..., method=...)` in `apps/api/main_v2.py` and `logger.warning("Rate limit degraded: bypassing due to Redis failure", error=str(e))` in `apps/api/middleware/rate_limit.py`.
- Some modules still mix in f-string logging, especially older router/service code such as `apps/api/routers/collection_v2.py` and parts of `apps/api/main_v2.py`. For consistency, new API code should prefer structured event names plus keyword fields.
- Request logging redacts sensitive fields before emission. `_mask_sensitive_fields()` and `_mask_sensitive_value()` in `apps/api/middleware/logging.py` are the repository standard for masking headers, query params, and tokens.
- Script-package logging is mixed: `packages/scripts/prompt_improvement/jury_prompt_improver.py` uses stdlib `logging`, `packages/scripts/evaluation/data_loading.py` uses `print`, and shared utilities are not consistently structured.

## Comments and Documentation Style

**Inferred from code:**
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

---

*Convention analysis: 2026-04-05*

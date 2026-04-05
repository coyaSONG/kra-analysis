# Phase 01 Research: Runtime Guardrails

**Date:** 2026-04-05
**Phase:** 01 - Runtime Guardrails
**Requirements:** HEALTH-01, HEALTH-02, HEALTH-03

## Objective

Plan Phase 1 so the API runtime exposes one trustworthy contract for degraded health, request logging, and auth/policy typing without pulling in adjacent scopes like durable queue work, API key hashing, or schema baseline cleanup.

## Current State

### Health
- `apps/api/routers/health.py` already wraps Redis access with `get_optional_redis()`, but the detailed health path still collapses Redis into a boolean `"healthy"` / `"unhealthy"` result.
- `apps/api/bootstrap/runtime.py:ObservabilityFacade.build_health_snapshot()` only accepts `redis_ok: bool`, so it cannot represent `unavailable` vs `error`.
- Existing tests already expect HTTP 200 on degraded health paths:
  - `apps/api/tests/unit/test_health_detailed_branches.py`
  - `apps/api/tests/unit/test_health_dynamic.py`
  - `apps/api/tests/integration/test_api_endpoints.py`

### Logging
- `apps/api/main_v2.py` mounts `RequestLoggingMiddleware`, while `apps/api/middleware/logging.py:LoggingMiddleware` owns request id, redaction, and structured lifecycle logging.
- Current test coverage is split across both assumptions:
  - `apps/api/tests/unit/test_middleware_logging.py`
  - `apps/api/tests/unit/test_logging_redaction.py`
  - `apps/api/tests/unit/test_logging_middleware_post_body.py`
  - `apps/api/tests/unit/test_logging_middleware_error.py`
- `apps/api/middleware/policy_accounting.py` depends on `request.state.request_id`, so request-id generation must stay compatible with that middleware.

### Auth / Policy
- Routers already consume `AuthenticatedPrincipal` through `require_action()` in `apps/api/routers/collection_v2.py` and `apps/api/routers/jobs_v2.py`.
- `apps/api/dependencies/auth.py` still exposes ORM-oriented helpers such as `require_api_key_record()` and request-time counter mutation in `verify_api_key()`.
- Existing auth/policy tests provide a good seam-preserving baseline:
  - `apps/api/tests/unit/test_auth_deps.py`
  - `apps/api/tests/unit/test_auth.py`
  - `apps/api/tests/unit/test_auth_extended.py`
  - `apps/api/tests/unit/test_auth_resource_access.py`
  - `apps/api/tests/integration/test_policy_accounting.py`

## Recommended Implementation Approach

### 1. Degraded Health Contract
- Keep `/health/detailed` fail-open for Redis and always return HTTP 200 unless the handler itself crashes.
- Extend `ObservabilityFacade.build_health_snapshot()` so Redis status is represented with richer component states rather than only booleans.
- Normalize response semantics:
  - overall `status = healthy` only when DB, Redis, and background tasks are all healthy
  - overall `status = degraded` when Redis is unavailable/error or background tasks are degraded
  - DB failure remains a component-status report, not an automatic transport failure
- Remove the branch that currently treats a Redis-like object without `ping()` as healthy.

### 2. Canonical Logging Path
- Collapse `LoggingMiddleware` behavior into `RequestLoggingMiddleware` instead of remounting the old middleware in `main_v2.py`.
- Preserve these behaviors in one canonical middleware:
  - request id creation and propagation to both `request.state` and `X-Request-ID`
  - sensitive field redaction through shared helpers
  - structured `request_started`, `request_completed`, `request_failed` events
  - optional small JSON request-body logging at debug level only
- Update tests so the canonical runtime middleware is the thing they validate.

### 3. Auth / Policy Typing
- Treat `AuthenticatedPrincipal` as the public router/policy contract everywhere request authorization crosses a boundary.
- Keep `APIKey` ORM internal to credential lookup, quota mutation, and persistence-only helper paths.
- Preserve current usage-accounting seam (`reserve` before request, `commit_request` after request); Phase 1 is not the time to redesign accounting architecture.

## Planner Constraints

- Do not add new endpoints or broaden product scope.
- Do not pull in job vocabulary cleanup, durable queue work, or schema baseline unification.
- Keep code changes centered on:
  - `apps/api/routers/health.py`
  - `apps/api/bootstrap/runtime.py`
  - `apps/api/middleware/logging.py`
  - `apps/api/main_v2.py`
  - `apps/api/middleware/policy_accounting.py`
  - `apps/api/dependencies/auth.py`
  - `apps/api/policy/*.py`
  - targeted health/logging/auth tests

## Reusable Patterns and Assets

- `ObservabilityFacade` is already the rendering seam for health and metrics; extend it instead of duplicating health formatting logic in the router.
- `FakeRedis` and `ASGITransport` fixtures from `apps/api/tests/platform/fixtures.py` are the standard infrastructure doubles for API tests.
- `_mask_sensitive_fields()` and `_mask_sensitive_value()` are the existing redaction helpers and should remain the one masking implementation.
- `require_action()` plus `UsageAccountant.reserve()` is the policy entry point the plan should preserve.

## Regression Risks

- Logging refactor can silently break `PolicyAccountingMiddleware` if request id is no longer written to `request.state`.
- Health refactor can pass fake-based tests but still miss uninitialized Redis behavior if the planner ignores the actual `get_redis()` / `check_redis_connection()` split.
- Auth seam cleanup can unintentionally double-count usage if lookup and reserve logic are rearranged without preserving current test expectations.

## Verification Guidance

### Targeted commands
- `cd apps/api && uv run pytest -q tests/unit/test_health_detailed_branches.py`
- `cd apps/api && uv run pytest -q tests/unit/test_health_dynamic.py`
- `cd apps/api && uv run pytest -q tests/unit/test_middleware_logging.py tests/unit/test_logging_redaction.py tests/unit/test_logging_middleware_post_body.py tests/unit/test_logging_middleware_error.py`
- `cd apps/api && uv run pytest -q tests/unit/test_auth_deps.py tests/unit/test_auth.py tests/unit/test_auth_extended.py tests/unit/test_auth_resource_access.py`
- `cd apps/api && uv run pytest -q tests/integration/test_policy_accounting.py tests/integration/test_api_endpoints.py`

### Full confidence command
- `cd apps/api && uv run pytest -q`

## Suggested Plan Shape

1. Health snapshot contract and degraded Redis tests
2. Logging middleware unification and request-id propagation
3. Auth/policy boundary cleanup plus accounting/resource-access regression checks
4. Integrated validation sweep and full test run

## Validation Architecture

### Test Infrastructure
- Framework: `pytest` + `pytest-asyncio` + `pytest-cov`
- Config files: `apps/api/pytest.ini`, `apps/api/.coveragerc`
- Quick run command: `cd apps/api && uv run pytest -q tests/unit/test_health_detailed_branches.py tests/unit/test_health_dynamic.py tests/unit/test_middleware_logging.py tests/unit/test_logging_redaction.py tests/unit/test_auth_deps.py`
- Full suite command: `cd apps/api && uv run pytest -q`
- Estimated quick feedback runtime: under 30 seconds for targeted files

### Sampling Strategy
- After each health/logging/auth task commit: run the smallest targeted pytest subset for the touched area
- After each plan wave: run a broader phase subset including integration checks
- Before phase verification: run the full API suite

### Validation Gaps to cover in planning
- explicit assertion for Redis `unavailable` / `error` distinction in detailed health
- request id propagation from canonical logging path into `PolicyAccountingMiddleware`
- principal-first auth boundary coverage without re-exposing ORM types at route edges

## Bottom Line

Phase 1 is a focused runtime-contract cleanup. The best plan is one that makes health degradation explicit, merges runtime logging into one canonical middleware path, and standardizes auth/policy typing around `AuthenticatedPrincipal` with targeted regression tests at each step.

# Phase 01: Runtime Guardrails - Research

**Researched:** 2026-04-05 [VERIFIED: .planning/phases/01-runtime-guardrails/01-CONTEXT.md]  
**Domain:** FastAPI runtime guardrails for degraded health, canonical request logging, and auth/policy contract unification [VERIFIED: .planning/phases/01-runtime-guardrails/01-CONTEXT.md][VERIFIED: apps/api/main_v2.py]  
**Confidence:** HIGH [VERIFIED: repo code reads 2026-04-05][VERIFIED: targeted pytest runs 2026-04-05]

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions [VERIFIED: .planning/phases/01-runtime-guardrails/01-CONTEXT.md]
- **D-01:** Redis는 `health/detailed` 경로에서 optional dependency로 취급한다. Redis 미초기화, 연결 실패, `ping()` 실패가 있어도 `/health/detailed`는 항상 HTTP 200을 반환한다.
- **D-02:** 상세 헬스 응답의 overall `status`는 DB, Redis, background task 상태를 종합해 계산하되, Redis 문제는 `degraded`로 표현하고 요청 자체를 500으로 실패시키지 않는다.
- **D-03:** Redis 컴포넌트 상태는 단순 boolean이 아니라 `healthy` / `unavailable` / `error`처럼 원인을 구분할 수 있는 방향으로 정리한다. fake나 잘못 주입된 객체를 `healthy`로 오인하는 현재 동작은 Phase 1에서 제거한다.
- **D-04:** `RequestLoggingMiddleware`를 canonical request logging 경로로 삼고, 현재 `LoggingMiddleware`가 가진 request id 부여, 민감정보 마스킹, start/complete/error 이벤트 책임을 여기에 흡수한다.
- **D-05:** 운영 기본 로그는 구조화된 `request_started` / `request_completed` / `request_failed` 이벤트를 유지하고, `X-Request-ID`는 하나의 middleware 경로에서 생성/전파한다.
- **D-06:** 요청 바디 로깅은 작은 JSON body에 한해 debug 레벨에서만 허용하고, 헤더/쿼리/body redaction 규칙은 공통 마스킹 헬퍼 하나로 통일한다.
- **D-07:** router 및 policy 경계의 canonical caller 타입은 `AuthenticatedPrincipal`로 통일한다. `APIKey` ORM은 credential lookup과 persistence update 단계 내부에서만 사용한다.
- **D-08:** `require_principal()` / `require_action()` 체인을 public dependency path로 간주하고, planner는 `require_api_key_record()`를 외부 계약처럼 확장하지 않는다.
- **D-09:** Usage accounting은 principal 기반 예약/커밋 seam을 유지하되, raw key hashing 같은 저장 방식 변경은 이 phase 범위에 넣지 않는다. 이번 phase의 목표는 type contract 통일과 request path 신뢰성 회복이다.

### Claude's Discretion [VERIFIED: .planning/phases/01-runtime-guardrails/01-CONTEXT.md]
- Phase 1 구현에는 runtime code 수정과 이를 증명하는 unit/integration test 정리가 포함될 수 있다.
- broader docs truth cleanup, durable queue 논의, schema baseline 재정의는 이 phase에서 새 scope로 끌어오지 않는다.
- request id를 logging middleware가 소유할지 shared helper가 소유할지는 planner가 정하되, 최종 관찰 가능한 계약은 single source of truth여야 한다.

### Deferred Ideas (OUT OF SCOPE) [VERIFIED: .planning/phases/01-runtime-guardrails/01-CONTEXT.md]
- API key hashing / public credential id 도입 — future security-focused phase
- durable queue 또는 orphaned job reconciliation — Phase 4 이후 execution platform work
- schema baseline unification and migration-only bootstrap — Phase 3
- broad docs truth cleanup outside runtime guardrails — Phase 6
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| HEALTH-01 | Operator can call `/health/detailed` with Redis unavailable and still receive HTTP 200 with an explicit degraded component status. [VERIFIED: .planning/REQUIREMENTS.md] | Keep the existing `/health/detailed` route and `ObservabilityFacade` seam, but change Redis evaluation from boolean to explicit component status and add degraded-path tests under the real app harness. [VERIFIED: apps/api/routers/health.py][VERIFIED: apps/api/bootstrap/runtime.py][VERIFIED: apps/api/tests/unit/test_health_detailed_branches.py][VERIFIED: apps/api/tests/integration/test_api_endpoints.py] |
| HEALTH-02 | Operator can rely on one canonical request logging path that redacts sensitive request data consistently in runtime and tests. [VERIFIED: .planning/REQUIREMENTS.md] | Move `LoggingMiddleware` responsibilities into the middleware actually mounted by `create_app()`, then retarget logging tests to `RequestLoggingMiddleware` or the app factory path. [VERIFIED: apps/api/main_v2.py][VERIFIED: apps/api/middleware/logging.py][VERIFIED: apps/api/tests/unit/test_middleware_logging.py][VERIFIED: apps/api/tests/unit/test_logging_redaction.py] |
| HEALTH-03 | Contributor can use one consistent authentication and authorization contract without type mismatches across dependency, policy, and accounting paths. [VERIFIED: .planning/REQUIREMENTS.md] | Preserve `AuthenticatedPrincipal` and `require_action()` as the public contract, keep `APIKey` inside lookup/update helpers, and add tests that prove request state, reservation, and owner identity stay aligned. [VERIFIED: apps/api/dependencies/auth.py][VERIFIED: apps/api/policy/principal.py][VERIFIED: apps/api/policy/accounting.py][VERIFIED: apps/api/middleware/policy_accounting.py] |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Python execution and dependency management should stay on `uv` with `python3` semantics. [VERIFIED: CLAUDE.md]
- `.env`, `data/`, and `KRA_PUBLIC_API_GUIDE.md` are protected and must not be deleted by this phase. [VERIFIED: CLAUDE.md]
- Existing docs should be checked before adding new docs, and duplicate documentation should be avoided. [VERIFIED: CLAUDE.md]
- Significant refactor work should be driven by an ExecPlan. [VERIFIED: CLAUDE.md]
- `win_odds=0` filtering and enriched-data-first rules are project-level constraints but unrelated to Phase 01 scope, so planner should leave them untouched. [VERIFIED: CLAUDE.md][VERIFIED: .planning/phases/01-runtime-guardrails/01-CONTEXT.md]

## Summary

- Phase 01 can be planned as a contract-unification pass inside the existing FastAPI app factory; the core seams already exist as `ObservabilityFacade`, `RequestLoggingMiddleware`, and `AuthenticatedPrincipal`. [VERIFIED: apps/api/bootstrap/runtime.py][VERIFIED: apps/api/main_v2.py][VERIFIED: apps/api/policy/principal.py]
- The main repo drift is between mounted runtime paths and tested paths: `create_app()` mounts `RequestLoggingMiddleware`, but current logging tests still instantiate `LoggingMiddleware` directly. [VERIFIED: apps/api/main_v2.py][VERIFIED: apps/api/tests/unit/test_middleware_logging.py][VERIFIED: apps/api/tests/unit/test_logging_redaction.py]
- Focused health, logging, auth, and policy tests currently pass only when coverage addopts are overridden; default `pytest` exits non-zero on small samples because `apps/api/pytest.ini` enforces repo-wide coverage. [VERIFIED: apps/api/pytest.ini][VERIFIED: targeted pytest runs 2026-04-05]

**Primary recommendation:** Plan this phase as three small slices: explicit degraded Redis status, canonical request logging consolidation, and principal-first auth/policy tests, with contract tests written or corrected before each runtime edit. [VERIFIED: .planning/phases/01-runtime-guardrails/01-CONTEXT.md][VERIFIED: docs/plans/2026-03-19-architecture-remediation-execplan.md]

## Required Changes

### HEALTH-01
- Replace the boolean Redis path in `detailed_health_check()` with a helper that classifies Redis as `healthy`, `unavailable`, or `error`; the current truthy-object-without-`ping` branch at `routers/health.py:38-48` violates locked decision `D-03`. [VERIFIED: apps/api/routers/health.py][VERIFIED: .planning/phases/01-runtime-guardrails/01-CONTEXT.md]
- Extend `ObservabilityFacade.build_health_snapshot()` so the response can expose explicit Redis component state while still computing top-level overall status in one place. [VERIFIED: apps/api/bootstrap/runtime.py][VERIFIED: .planning/phases/01-runtime-guardrails/01-CONTEXT.md]
- Keep `/health/detailed` on HTTP 200 for Redis missing/failing paths and let degraded state live in the payload, not the status code. [VERIFIED: .planning/REQUIREMENTS.md][VERIFIED: apps/api/tests/unit/test_health_detailed_branches.py]
- Preserve the router/runtime seam already used by current tests; the right plan is to refactor health probing behind helpers, not to move health rendering out of `runtime.observability`. [VERIFIED: apps/api/routers/health.py][VERIFIED: apps/api/bootstrap/runtime.py]

**Test changes**
- Update unit health tests to assert the explicit Redis states required by `D-03`; the current tests only assert `"unhealthy"`. [VERIFIED: apps/api/tests/unit/test_health_detailed_branches.py][VERIFIED: .planning/phases/01-runtime-guardrails/01-CONTEXT.md]
- Add at least one app-level degraded Redis integration test next to `TestHealthEndpoints` so the real dependency override path proves HTTP 200 + degraded payload under the mounted app. [VERIFIED: apps/api/tests/integration/test_api_endpoints.py][VERIFIED: apps/api/tests/platform/fixtures.py]
- Keep the existing background-task status coverage from `test_health_dynamic.py`; it already exercises the `AppRuntime` injection pattern the planner should preserve. [VERIFIED: apps/api/tests/unit/test_health_dynamic.py][VERIFIED: apps/api/tests/platform/fixtures.py]

### HEALTH-02
- Consolidate `LoggingMiddleware` responsibilities into `RequestLoggingMiddleware`: request id generation, `request_started` / `request_completed` / `request_failed` events, sensitive header/query masking, and `X-Request-ID` propagation currently live only in the legacy class. [VERIFIED: apps/api/middleware/logging.py][VERIFIED: .planning/phases/01-runtime-guardrails/01-CONTEXT.md]
- Have the canonical logger set `request.state.request_id` as well as the response header so `PolicyAccountingMiddleware` stops being a competing source of request ids. [VERIFIED: apps/api/middleware/policy_accounting.py][VERIFIED: apps/api/middleware/logging.py][VERIFIED: .planning/phases/01-runtime-guardrails/01-CONTEXT.md]
- Keep request-body logging debug-only and size-limited, but route body redaction through the same masking helper as headers and query params; current body logging emits raw JSON. [VERIFIED: apps/api/middleware/logging.py][VERIFIED: .planning/phases/01-runtime-guardrails/01-CONTEXT.md]
- Preserve the body replay pattern after reading `request.body()` so POST/PATCH handlers keep working. [VERIFIED: apps/api/middleware/logging.py]

**Test changes**
- Retarget or replace `tests/unit/test_middleware_logging.py`, `tests/unit/test_logging_redaction.py`, `tests/unit/test_logging_middleware_post_body.py`, and `tests/unit/test_logging_middleware_error.py` so they exercise `RequestLoggingMiddleware` or `create_app()`, not `LoggingMiddleware`. [VERIFIED: apps/api/tests/unit/test_middleware_logging.py][VERIFIED: apps/api/tests/unit/test_logging_redaction.py][VERIFIED: apps/api/tests/unit/test_logging_middleware_post_body.py][VERIFIED: apps/api/tests/unit/test_logging_middleware_error.py][VERIFIED: apps/api/main_v2.py]
- Add assertions for `request.state.request_id` and header consistency on the real middleware chain because current tests only check the response header. [VERIFIED: apps/api/tests/unit/test_middleware_logging.py][VERIFIED: apps/api/middleware/policy_accounting.py]
- Add a debug-body redaction test for a small JSON payload containing keys like `api_key`, `authorization`, or `serviceKey`; current redaction tests cover headers/query only. [VERIFIED: apps/api/tests/unit/test_logging_redaction.py][VERIFIED: apps/api/middleware/logging.py]

### HEALTH-03
- Keep router dependencies principal-first; `collection_v2.py` and `jobs_v2.py` already accept `AuthenticatedPrincipal = Depends(require_action(...))`, so planner should preserve that pattern instead of expanding `require_api_key_record()` as a public type. [VERIFIED: apps/api/routers/collection_v2.py][VERIFIED: apps/api/routers/jobs_v2.py][VERIFIED: .planning/phases/01-runtime-guardrails/01-CONTEXT.md]
- Leave `APIKey` ORM usage inside lookup/update helpers like `verify_api_key()` and compatibility-only helpers like `require_resource_access()`; that is where persistence-side updates happen today. [VERIFIED: apps/api/dependencies/auth.py]
- Preserve the `UsageAccountant.reserve()` then `PolicyAccountingMiddleware.commit_request()` seam; it already aligns with the locked decision that accounting remains reservation/commit based. [VERIFIED: apps/api/dependencies/auth.py][VERIFIED: apps/api/policy/accounting.py][VERIFIED: apps/api/middleware/policy_accounting.py]
- Guard against contract drift between `principal.owner_ref`, `credential_id`, and persisted `UsageEvent.owner_ref`; that alignment is how job ownership and usage accounting currently work. [VERIFIED: apps/api/policy/authentication.py][VERIFIED: apps/api/policy/accounting.py][VERIFIED: apps/api/tests/integration/test_policy_accounting.py]

**Test changes**
- Keep existing `require_principal()` normalization tests, but add direct tests around `require_action()` to prove it writes `request.state.principal`, `request.state.policy_action`, and `request.state.usage_reservation`. [VERIFIED: apps/api/tests/unit/test_auth_deps.py][VERIFIED: apps/api/dependencies/auth.py]
- Expand integration coverage in `test_policy_accounting.py` to assert request id persistence as well as action/owner/path; current tests do not check request-id correlation. [VERIFIED: apps/api/tests/integration/test_policy_accounting.py][VERIFIED: apps/api/middleware/policy_accounting.py]
- Mark `test_policy_accounting.py` with `@pytest.mark.integration` or the repo’s `run_quality_ci.sh integration` path will skip it entirely. [VERIFIED: apps/api/tests/integration/test_policy_accounting.py][VERIFIED: apps/api/scripts/run_quality_ci.sh]

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | `>=0.115.5` in repo config and `0.118.0` in the active `uv` environment. [VERIFIED: apps/api/pyproject.toml][VERIFIED: runtime import versions 2026-04-05] | App factory, middleware chain, dependency injection, and route mounting. [VERIFIED: apps/api/main_v2.py] | All Phase 01 contracts are already expressed at the FastAPI app boundary, so planner should preserve this runtime shell. [VERIFIED: apps/api/main_v2.py] |
| structlog | `>=24.4.0` in repo config and `25.4.0` in the active `uv` environment. [VERIFIED: apps/api/pyproject.toml][VERIFIED: runtime import versions 2026-04-05] | Structured request and operational logs. [VERIFIED: apps/api/main_v2.py][VERIFIED: apps/api/middleware/logging.py] | Locked decision `D-05` explicitly depends on stable structured event names. [VERIFIED: .planning/phases/01-runtime-guardrails/01-CONTEXT.md] |
| SQLAlchemy async ORM | `>=2.0.36` in repo config and `2.0.43` in the active `uv` environment. [VERIFIED: apps/api/pyproject.toml][VERIFIED: runtime import versions 2026-04-05] | DB-backed API-key lookup and append-only usage accounting. [VERIFIED: apps/api/dependencies/auth.py][VERIFIED: apps/api/policy/accounting.py] | HEALTH-03 is a contract cleanup, not a persistence rewrite. [VERIFIED: .planning/REQUIREMENTS.md] |
| redis-py asyncio | `>=5.2.1` in repo config and `6.4.0` in the active `uv` environment. [VERIFIED: apps/api/pyproject.toml][VERIFIED: runtime import versions 2026-04-05] | Optional Redis dependency for health probing, rate limiting, cache, and background state. [VERIFIED: apps/api/infrastructure/redis_client.py][VERIFIED: apps/api/middleware/rate_limit.py] | Phase 01 should standardize degraded Redis reporting, not replace Redis usage. [VERIFIED: .planning/phases/01-runtime-guardrails/01-CONTEXT.md] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| HTTPX | `>=0.28.0` in repo config and `0.28.1` in the active `uv` environment. [VERIFIED: apps/api/pyproject.toml][VERIFIED: runtime import versions 2026-04-05] | In-process ASGI contract tests. [VERIFIED: apps/api/tests/platform/fixtures.py] | Use for middleware and route integration tests that must hit the real app without a live server. [VERIFIED: apps/api/tests/platform/fixtures.py] |
| pytest + pytest-asyncio | `pytest>=8.3.4`, `pytest-asyncio>=0.25.0` in repo config and `pytest 8.4.2` in the active `uv` environment. [VERIFIED: apps/api/pyproject.toml][VERIFIED: uv run pytest --version 2026-04-05] | Async unit and integration tests. [VERIFIED: apps/api/pytest.ini][VERIFIED: apps/api/tests/unit/test_health_dynamic.py] | Use the existing async test harness and override `addopts` for focused sampling. [VERIFIED: apps/api/pytest.ini][VERIFIED: targeted pytest runs 2026-04-05] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Rebuilding health or logging around new service objects. [VERIFIED: apps/api/bootstrap/runtime.py][VERIFIED: apps/api/middleware/logging.py] | Keep the existing runtime seam and delete duplicate responsibility. [VERIFIED: .planning/phases/01-runtime-guardrails/01-CONTEXT.md] | Brownfield risk is lower because current routers, fixtures, and integration tests already depend on these seams. [VERIFIED: apps/api/tests/platform/fixtures.py][VERIFIED: docs/plans/2026-03-19-architecture-remediation-execplan.md] |
| Making `APIKey` the public router dependency again. [VERIFIED: apps/api/dependencies/auth.py] | Keep `AuthenticatedPrincipal` public and `APIKey` internal. [VERIFIED: apps/api/policy/principal.py][VERIFIED: .planning/phases/01-runtime-guardrails/01-CONTEXT.md] | This matches the current router code and avoids widening the public auth contract mid-phase. [VERIFIED: apps/api/routers/collection_v2.py][VERIFIED: apps/api/routers/jobs_v2.py] |

**Installation:** Existing repo commands are sufficient for this phase. [VERIFIED: AGENTS.md][VERIFIED: apps/api/pyproject.toml]
```bash
pnpm i
uv sync --group dev
```

## Architecture Patterns

### Recommended Project Structure
```text
apps/api/
├── bootstrap/          # runtime-level rendering and app-scoped observability seam
├── routers/            # thin HTTP handlers and dependency boundaries
├── middleware/         # request/response cross-cutting behavior
├── dependencies/       # auth entrypoints and legacy compatibility helpers
├── policy/             # principal, authorization, accounting contracts
└── tests/
    ├── unit/           # seam-level contract tests
    ├── integration/    # app-factory/ASGI contract tests
    └── platform/       # shared fixtures, fakes, and harness state
```
[VERIFIED: apps/api/main_v2.py][VERIFIED: apps/api/dependencies/auth.py][VERIFIED: apps/api/policy/principal.py][VERIFIED: apps/api/tests/platform/fixtures.py]

### Pattern 1: Runtime Rendering Stays Behind `ObservabilityFacade`
**What:** Health and metrics rendering are already centralized in `ObservabilityFacade`. [VERIFIED: apps/api/bootstrap/runtime.py]  
**When to use:** Any Phase 01 change that affects the health payload or metrics output should pass through this facade instead of building ad hoc dicts in routers. [VERIFIED: apps/api/bootstrap/runtime.py][VERIFIED: apps/api/routers/health.py][VERIFIED: apps/api/routers/metrics.py]  
**Example:**
```python
# Source: apps/api/bootstrap/runtime.py
return runtime.observability.build_health_snapshot(
    db_ok=db_ok,
    redis_ok=redis_ok,
    background_status=background_stats['status'],
    version=settings.version,
    now=time.time(),
)
```

### Pattern 2: App-Factoried Tests With Dependency Overrides
**What:** The repo’s stable integration pattern is `create_app()` + `dependency_overrides` + `ASGITransport`. [VERIFIED: apps/api/tests/platform/fixtures.py][VERIFIED: apps/api/main_v2.py]  
**When to use:** Use this for HEALTH-01 and HEALTH-02 app-level tests so middleware order and request state are exercised under the real app. [VERIFIED: apps/api/tests/platform/fixtures.py][VERIFIED: apps/api/main_v2.py]  
**Example:**
```python
# Source: apps/api/tests/platform/fixtures.py
api_app = create_app()
api_app.dependency_overrides[get_optional_redis] = override_get_optional_redis
transport = ASGITransport(app=api_app)
```

### Pattern 3: Principal-First Router Dependencies
**What:** Public protected routes already accept `AuthenticatedPrincipal` through `require_action(...)`. [VERIFIED: apps/api/routers/collection_v2.py][VERIFIED: apps/api/routers/jobs_v2.py]  
**When to use:** HEALTH-03 changes should reinforce this boundary and keep `APIKey` hidden behind auth lookup/update helpers. [VERIFIED: apps/api/dependencies/auth.py][VERIFIED: .planning/phases/01-runtime-guardrails/01-CONTEXT.md]  
**Example:**
```python
# Source: apps/api/routers/jobs_v2.py
principal: AuthenticatedPrincipal = Depends(require_action('jobs.read'))
```

### Anti-Patterns to Avoid
- **Boolean-only Redis health:** Current `redis_ok` loses the distinction between missing Redis and broken Redis. [VERIFIED: apps/api/routers/health.py][VERIFIED: .planning/phases/01-runtime-guardrails/01-CONTEXT.md]
- **Testing legacy middleware instead of mounted middleware:** Current logging tests pass against `LoggingMiddleware` even though production mounts `RequestLoggingMiddleware`. [VERIFIED: apps/api/main_v2.py][VERIFIED: apps/api/tests/unit/test_middleware_logging.py]
- **Letting accounting mint the canonical request id:** `PolicyAccountingMiddleware` should remain a fallback, not the source of truth. [VERIFIED: apps/api/middleware/policy_accounting.py][VERIFIED: .planning/phases/01-runtime-guardrails/01-CONTEXT.md]
- **Expanding `require_api_key_record()` into the public contract:** Locked decision `D-08` forbids that direction. [VERIFIED: .planning/phases/01-runtime-guardrails/01-CONTEXT.md]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Health rendering | Per-route response assembly duplicated in router code. [VERIFIED: apps/api/routers/health.py] | `ObservabilityFacade` as the rendering source of truth. [VERIFIED: apps/api/bootstrap/runtime.py] | `/health/detailed` and `/metrics` already share this seam. [VERIFIED: apps/api/bootstrap/runtime.py][VERIFIED: apps/api/routers/metrics.py] |
| Request-id propagation | Separate request-id generation in multiple middleware layers. [VERIFIED: apps/api/middleware/logging.py][VERIFIED: apps/api/middleware/policy_accounting.py] | One canonical logging middleware plus fallback-only accounting behavior. [VERIFIED: .planning/phases/01-runtime-guardrails/01-CONTEXT.md] | Duplicate ownership is the current drift vector. [VERIFIED: apps/api/middleware/logging.py][VERIFIED: apps/api/middleware/policy_accounting.py] |
| Auth boundary types | New dict/DTO caller shape parallel to policy primitives. [VERIFIED: apps/api/policy/principal.py] | `AuthenticatedPrincipal`. [VERIFIED: apps/api/policy/principal.py] | Routers, authorization, and accounting already understand this type. [VERIFIED: apps/api/routers/collection_v2.py][VERIFIED: apps/api/routers/jobs_v2.py][VERIFIED: apps/api/policy/accounting.py] |
| Test harnesses | Bespoke live-server or manual fixture stacks for every test file. [VERIFIED: apps/api/tests/platform/fixtures.py] | Existing `ASGITransport`, `FakeRedis`, in-memory SQLite, and `create_app()` overrides. [VERIFIED: apps/api/tests/platform/fixtures.py] | The repo already ships a deterministic harness that matches Phase 01 needs. [VERIFIED: apps/api/tests/platform/fixtures.py] |

**Key insight:** The right plan deletes duplicate responsibility; it does not introduce a new runtime layer. [VERIFIED: docs/plans/2026-03-19-architecture-remediation-execplan.md][VERIFIED: .planning/phases/01-runtime-guardrails/01-CONTEXT.md]

## Common Pitfalls

### Pitfall 1: Health Checks That Reintroduce 500s
**What goes wrong:** `/health/detailed` fails the request instead of reporting degraded Redis state. [VERIFIED: .planning/REQUIREMENTS.md][VERIFIED: .planning/phases/01-runtime-guardrails/01-CONTEXT.md]  
**Why it happens:** Redis probing logic is spread across `get_optional_redis()`, direct `ping()`, and `check_redis_connection()`. [VERIFIED: apps/api/routers/health.py][VERIFIED: apps/api/infrastructure/redis_client.py]  
**How to avoid:** Isolate Redis classification in one helper and make the router convert only probe results to payload. [VERIFIED: apps/api/routers/health.py][VERIFIED: apps/api/bootstrap/runtime.py]  
**Warning signs:** Tests need to patch multiple Redis call sites to simulate one degraded case. [VERIFIED: apps/api/tests/unit/test_health_detailed_branches.py]

### Pitfall 2: Green Tests on the Wrong Logging Contract
**What goes wrong:** Logging unit tests stay green while the real app uses a different middleware class. [VERIFIED: apps/api/main_v2.py][VERIFIED: apps/api/tests/unit/test_middleware_logging.py]  
**Why it happens:** `LoggingMiddleware` and `RequestLoggingMiddleware` coexist in one module with split responsibility. [VERIFIED: apps/api/middleware/logging.py]  
**How to avoid:** Make the mounted middleware the canonical test subject and shrink or remove direct legacy middleware tests. [VERIFIED: apps/api/main_v2.py][VERIFIED: apps/api/tests/platform/fixtures.py]  
**Warning signs:** No test around `create_app()` asserts `request_started`, `request_completed`, or `request_failed`. [VERIFIED: apps/api/main_v2.py][VERIFIED: apps/api/tests/integration/test_api_endpoints.py]

### Pitfall 3: Request Body Logging Breaks POST Paths
**What goes wrong:** Reading the request body for logging makes downstream handlers see an empty body. [VERIFIED: apps/api/middleware/logging.py]  
**Why it happens:** The middleware must restore the ASGI receive channel after consuming `request.body()`. [VERIFIED: apps/api/middleware/logging.py]  
**How to avoid:** Preserve the existing replay pattern or replace it with an equivalent implementation before adding new redaction logic. [VERIFIED: apps/api/middleware/logging.py]  
**Warning signs:** POST integration tests start failing after logging refactors even though GET tests stay green. [VERIFIED: apps/api/tests/unit/test_logging_middleware_post_body.py]

### Pitfall 4: Invisible Integration Tests
**What goes wrong:** CI or local integration sampling skips policy-accounting tests. [VERIFIED: apps/api/scripts/run_quality_ci.sh][VERIFIED: apps/api/tests/integration/test_policy_accounting.py]  
**Why it happens:** `run_quality_ci.sh integration` filters on `-m integration`, but `test_policy_accounting.py` currently lacks that marker. [VERIFIED: apps/api/scripts/run_quality_ci.sh][VERIFIED: apps/api/tests/integration/test_policy_accounting.py]  
**How to avoid:** Add the integration marker or run the file explicitly in quick verification commands. [VERIFIED: apps/api/scripts/run_quality_ci.sh][VERIFIED: targeted pytest runs 2026-04-05]  
**Warning signs:** A targeted file run passes, but the integration stage reports zero selected tests. [VERIFIED: targeted pytest runs 2026-04-05]

## Code Examples

### Real App Middleware Mount Point
```python
# Source: apps/api/main_v2.py
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(PolicyAccountingMiddleware)
app.add_middleware(
    RateLimitMiddleware,
    calls=settings.rate_limit_calls,
    period=settings.rate_limit_period,
)
```
[VERIFIED: apps/api/main_v2.py]

### Principal Reservation Seam
```python
# Source: apps/api/dependencies/auth.py
async def dependency(
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_principal),
) -> AuthenticatedPrincipal:
    await _policy_authorizer.authorize(principal, action)
    reservation = await _usage_accountant.reserve(principal, action)
    request.state.principal = principal
    request.state.policy_action = action
    request.state.usage_reservation = reservation
    return principal
```
[VERIFIED: apps/api/dependencies/auth.py]

### In-Process API Test Harness
```python
# Source: apps/api/tests/platform/fixtures.py
transport = ASGITransport(app=api_app)
async with AsyncClient(transport=transport, base_url='http://test') as http_client:
    yield http_client
```
[VERIFIED: apps/api/tests/platform/fixtures.py]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Legacy logging contract centered on `LoggingMiddleware` tests. [VERIFIED: apps/api/tests/unit/test_middleware_logging.py] | The mounted runtime path is `RequestLoggingMiddleware`. [VERIFIED: apps/api/main_v2.py] | Already true in the current app factory. [VERIFIED: apps/api/main_v2.py] | Planner should move tests and responsibilities to the mounted middleware, not the legacy test target. [VERIFIED: apps/api/main_v2.py][VERIFIED: apps/api/tests/unit/test_middleware_logging.py] |
| Boolean Redis health in payload rendering. [VERIFIED: apps/api/bootstrap/runtime.py][VERIFIED: apps/api/routers/health.py] | Locked requirement is explicit Redis component state with degraded overall status. [VERIFIED: .planning/phases/01-runtime-guardrails/01-CONTEXT.md] | Locked on 2026-04-05 in Phase 01 context. [VERIFIED: .planning/phases/01-runtime-guardrails/01-CONTEXT.md] | Planner should treat response-shape refinement as required phase work, not optional cleanup. [VERIFIED: .planning/REQUIREMENTS.md] |
| Mixed `APIKey` and principal-style auth helpers coexisting. [VERIFIED: apps/api/dependencies/auth.py] | Public router/policy path already uses `AuthenticatedPrincipal`. [VERIFIED: apps/api/routers/collection_v2.py][VERIFIED: apps/api/routers/jobs_v2.py] | Already true in current routes. [VERIFIED: apps/api/routers/collection_v2.py][VERIFIED: apps/api/routers/jobs_v2.py] | Phase 01 should finish the contract cleanup by testing and preserving that public boundary. [VERIFIED: .planning/phases/01-runtime-guardrails/01-CONTEXT.md] |

**Deprecated/outdated:**
- Treating `LoggingMiddleware` tests as proof of production logging behavior is outdated. [VERIFIED: apps/api/main_v2.py][VERIFIED: apps/api/tests/unit/test_middleware_logging.py]
- Treating uninitialized Redis and broken Redis as the same undifferentiated boolean is outdated for this phase. [VERIFIED: .planning/phases/01-runtime-guardrails/01-CONTEXT.md][VERIFIED: apps/api/bootstrap/runtime.py]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | This research should remain fresh through 2026-05-05 unless Phase 01 code lands earlier. | Metadata | Low. It affects when the planner should refresh research, not the current technical recommendations. |

## Resolved Questions

1. **HEALTH-01 response shape**
   - Decision: Keep the existing flat response keys for Phase 1 and upgrade only the Redis value vocabulary. `data["redis"]` remains a flat field and must return `healthy`, `unavailable`, or `error`; do not introduce a nested component object in this phase. [RESOLVED 2026-04-05][VERIFIED: apps/api/tests/integration/test_api_endpoints.py][VERIFIED: .planning/phases/01-runtime-guardrails/01-CONTEXT.md]
   - Why: This preserves the smallest observable API change while satisfying locked decision `D-03` and keeping current health endpoint assertions easy to migrate. [VERIFIED: .planning/phases/01-runtime-guardrails/01-CONTEXT.md][VERIFIED: apps/api/tests/integration/test_api_endpoints.py]
   - Planning impact: `01-01-PLAN.md` must add an app-level integration case that asserts HTTP 200 plus the flat `redis` field carrying the new explicit vocabulary under degraded Redis conditions. [VERIFIED: .planning/phases/01-runtime-guardrails/01-01-PLAN.md]

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `python3` | local scripting and shell probes | ✓ | `3.14.3` | — [VERIFIED: python3 --version 2026-04-05] |
| `uv` | app test execution and dependency resolution | ✓ | `0.10.9` | — [VERIFIED: uv --version 2026-04-05] |
| `node` | workspace tooling | ✓ | `v24.11.0` | — [VERIFIED: node --version 2026-04-05] |
| `pnpm` | monorepo scripts | ✓ | `9.0.0` | — [VERIFIED: pnpm --version 2026-04-05] |
| `pytest` in `uv` env | phase validation | ✓ | `8.4.2` | — [VERIFIED: uv run pytest --version 2026-04-05] |
| Redis server | focused phase tests | Not required for test path | fake Redis via fixtures | `tests/platform/fixtures.py` overrides `get_redis` and `get_optional_redis`. [VERIFIED: apps/api/tests/platform/fixtures.py] |
| PostgreSQL server | focused phase tests | Not required for test path | in-memory SQLite via fixtures | `tests/platform/fixtures.py` creates `sqlite+aiosqlite:///:memory:` engines per test. [VERIFIED: apps/api/tests/platform/fixtures.py] |

**Missing dependencies with no fallback:**
- None for research or focused Phase 01 validation. [VERIFIED: apps/api/tests/platform/fixtures.py][VERIFIED: command probes 2026-04-05]

**Missing dependencies with fallback:**
- None. [VERIFIED: command probes 2026-04-05]

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `pytest 8.4.2` with `pytest-asyncio`, `pytest-cov`, and `pytest-timeout`. [VERIFIED: apps/api/pyproject.toml][VERIFIED: uv run pytest --version 2026-04-05] |
| Config file | `apps/api/pytest.ini`. [VERIFIED: apps/api/pytest.ini] |
| Quick run command | `cd apps/api && uv run pytest -v --tb=short --timeout=60 -o addopts='' <focused test files>`. [VERIFIED: targeted pytest runs 2026-04-05] |
| Full suite command | `pnpm -F @apps/api test`. [VERIFIED: apps/api/package.json] |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| HEALTH-01 | `/health/detailed` returns HTTP 200 and degraded Redis state when Redis is missing or failing. [VERIFIED: .planning/REQUIREMENTS.md] | unit + integration | `cd apps/api && uv run pytest -v --tb=short -o addopts='' tests/unit/test_health_detailed_branches.py tests/unit/test_health_dynamic.py` [VERIFIED: targeted pytest runs 2026-04-05] | ✅ existing unit files; degraded integration case missing in `tests/integration/test_api_endpoints.py`. [VERIFIED: apps/api/tests/unit/test_health_detailed_branches.py][VERIFIED: apps/api/tests/integration/test_api_endpoints.py] |
| HEALTH-02 | Real app logging path emits canonical events, consistent request id, and redacts sensitive data. [VERIFIED: .planning/REQUIREMENTS.md] | unit + integration | `cd apps/api && uv run pytest -v --tb=short --timeout=60 -o addopts='' tests/unit/test_middleware_logging.py tests/unit/test_logging_redaction.py tests/unit/test_logging_middleware_post_body.py tests/unit/test_logging_middleware_error.py` [VERIFIED: targeted pytest runs 2026-04-05] | ⚠️ files exist but target legacy `LoggingMiddleware`, so canonical coverage is missing. [VERIFIED: apps/api/tests/unit/test_middleware_logging.py][VERIFIED: apps/api/main_v2.py] |
| HEALTH-03 | `require_principal()` / `require_action()` / accounting share one principal contract and aligned request state. [VERIFIED: .planning/REQUIREMENTS.md] | unit + integration | `cd apps/api && uv run pytest -v --tb=short --timeout=60 -o addopts='' tests/unit/test_auth_deps.py tests/unit/test_auth_resource_access.py tests/integration/test_policy_accounting.py` [VERIFIED: targeted pytest runs 2026-04-05] | ✅ files exist; `test_policy_accounting.py` needs integration markers and request-id assertions. [VERIFIED: apps/api/tests/unit/test_auth_deps.py][VERIFIED: apps/api/tests/unit/test_auth_resource_access.py][VERIFIED: apps/api/tests/integration/test_policy_accounting.py] |

### Sampling Rate
- **Per task commit:** Run only the requirement-local files with `-o addopts=''` so coverage gating does not create false negatives on small samples. [VERIFIED: apps/api/pytest.ini][VERIFIED: targeted pytest runs 2026-04-05]
- **Per wave merge:** Run `bash apps/api/scripts/run_quality_ci.sh unit` plus explicit targeted integration files for health and policy accounting until all needed files carry the `integration` marker. [VERIFIED: apps/api/scripts/run_quality_ci.sh][VERIFIED: apps/api/tests/integration/test_policy_accounting.py]
- **Phase gate:** Run `pnpm -F @apps/api test` and `bash apps/api/scripts/run_quality_ci.sh integration` after marker cleanup. [VERIFIED: apps/api/package.json][VERIFIED: apps/api/scripts/run_quality_ci.sh]

### Wave 0 Gaps
- [ ] `apps/api/tests/integration/test_api_endpoints.py` — add degraded Redis case under real app wiring for HEALTH-01. [VERIFIED: apps/api/tests/integration/test_api_endpoints.py]
- [ ] `apps/api/tests/unit/test_middleware_logging.py` and friends — retarget to `RequestLoggingMiddleware` or move assertions into an app-factory test module for HEALTH-02. [VERIFIED: apps/api/tests/unit/test_middleware_logging.py][VERIFIED: apps/api/main_v2.py]
- [ ] `apps/api/tests/unit/test_logging_redaction.py` — add JSON body redaction assertions for HEALTH-02. [VERIFIED: apps/api/tests/unit/test_logging_redaction.py]
- [ ] `apps/api/tests/integration/test_policy_accounting.py` — add `@pytest.mark.integration` and request-id correlation assertions for HEALTH-03. [VERIFIED: apps/api/tests/integration/test_policy_accounting.py][VERIFIED: apps/api/scripts/run_quality_ci.sh]
- [ ] `apps/api/tests/unit/test_auth_deps.py` — add direct `require_action()` request-state contract coverage for HEALTH-03. [VERIFIED: apps/api/tests/unit/test_auth_deps.py][VERIFIED: apps/api/dependencies/auth.py]

## Security Domain

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | API-key verification through `require_api_key_record()` and principal normalization through `require_principal()`. [VERIFIED: apps/api/dependencies/auth.py] |
| V3 Session Management | no | This phase does not introduce session state; JWT helpers are optional and out of scope for runtime-guardrail work. [VERIFIED: apps/api/dependencies/auth.py][VERIFIED: .planning/phases/01-runtime-guardrails/01-CONTEXT.md] |
| V4 Access Control | yes | Action-level authorization via `PolicyAuthorizer` and principal-first router dependencies. [VERIFIED: apps/api/policy/authorization.py][VERIFIED: apps/api/routers/jobs_v2.py][VERIFIED: apps/api/routers/collection_v2.py] |
| V5 Input Validation | yes | FastAPI/Pydantic request validation and explicit API-key format checks in `verify_api_key()`. [VERIFIED: apps/api/dependencies/auth.py][VERIFIED: apps/api/models/collection_dto.py] |
| V6 Cryptography | no | No new cryptographic control is in scope; hashing redesign is explicitly deferred. [VERIFIED: .planning/phases/01-runtime-guardrails/01-CONTEXT.md] |

### Known Threat Patterns for This Stack
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| API key or token leakage in logs | Information Disclosure | Centralize masking and never log raw sensitive values outside the shared helper. [VERIFIED: apps/api/middleware/logging.py][VERIFIED: .planning/phases/01-runtime-guardrails/01-CONTEXT.md] |
| Broken access control from mixed public caller types | Elevation of Privilege | Keep `AuthenticatedPrincipal` as the public contract and avoid routing decisions on raw ORM objects. [VERIFIED: apps/api/policy/principal.py][VERIFIED: .planning/phases/01-runtime-guardrails/01-CONTEXT.md] |
| Ambiguous request-id ownership causing weak audit trails | Repudiation | Make one middleware the source of truth for request id and require accounting to consume it. [VERIFIED: apps/api/middleware/logging.py][VERIFIED: apps/api/middleware/policy_accounting.py] |

## Sources

### Primary (HIGH confidence)
- `.planning/phases/01-runtime-guardrails/01-CONTEXT.md` — locked decisions, discretion, and out-of-scope boundaries. [VERIFIED: .planning/phases/01-runtime-guardrails/01-CONTEXT.md]
- `.planning/REQUIREMENTS.md` — `HEALTH-01`, `HEALTH-02`, `HEALTH-03` requirement text. [VERIFIED: .planning/REQUIREMENTS.md]
- `docs/plans/2026-03-19-architecture-remediation-execplan.md` — remediation ordering and known drift areas. [VERIFIED: docs/plans/2026-03-19-architecture-remediation-execplan.md]
- `apps/api/main_v2.py` — real middleware and router wiring. [VERIFIED: apps/api/main_v2.py]
- `apps/api/bootstrap/runtime.py`, `apps/api/routers/health.py`, `apps/api/middleware/logging.py`, `apps/api/middleware/policy_accounting.py`, `apps/api/dependencies/auth.py`, `apps/api/policy/*.py` — runtime seams under Phase 01. [VERIFIED: apps/api/bootstrap/runtime.py][VERIFIED: apps/api/routers/health.py][VERIFIED: apps/api/middleware/logging.py][VERIFIED: apps/api/middleware/policy_accounting.py][VERIFIED: apps/api/dependencies/auth.py][VERIFIED: apps/api/policy/authentication.py][VERIFIED: apps/api/policy/accounting.py][VERIFIED: apps/api/policy/principal.py]
- `apps/api/tests/unit/*` and `apps/api/tests/integration/*` files listed in the task plus `apps/api/tests/platform/fixtures.py` — current coverage shape and harness patterns. [VERIFIED: apps/api/tests/unit/test_health_detailed_branches.py][VERIFIED: apps/api/tests/unit/test_health_dynamic.py][VERIFIED: apps/api/tests/unit/test_middleware_logging.py][VERIFIED: apps/api/tests/unit/test_logging_redaction.py][VERIFIED: apps/api/tests/unit/test_logging_middleware_post_body.py][VERIFIED: apps/api/tests/unit/test_logging_middleware_error.py][VERIFIED: apps/api/tests/unit/test_auth.py][VERIFIED: apps/api/tests/unit/test_auth_deps.py][VERIFIED: apps/api/tests/unit/test_auth_extended.py][VERIFIED: apps/api/tests/unit/test_auth_expired_key.py][VERIFIED: apps/api/tests/unit/test_auth_token_paths.py][VERIFIED: apps/api/tests/unit/test_auth_resource_access.py][VERIFIED: apps/api/tests/integration/test_api_endpoints.py][VERIFIED: apps/api/tests/integration/test_policy_accounting.py][VERIFIED: apps/api/tests/platform/fixtures.py]
- `apps/api/pytest.ini`, `apps/api/pyproject.toml`, `apps/api/scripts/run_quality_ci.sh`, `apps/api/package.json`, `package.json` — validation and execution contract. [VERIFIED: apps/api/pytest.ini][VERIFIED: apps/api/pyproject.toml][VERIFIED: apps/api/scripts/run_quality_ci.sh][VERIFIED: apps/api/package.json][VERIFIED: package.json]
- Local command probes on 2026-04-05 — environment versions and targeted pytest behavior. [VERIFIED: python3 --version 2026-04-05][VERIFIED: uv --version 2026-04-05][VERIFIED: node --version 2026-04-05][VERIFIED: pnpm --version 2026-04-05][VERIFIED: uv run pytest --version 2026-04-05][VERIFIED: targeted pytest runs 2026-04-05][VERIFIED: runtime import versions 2026-04-05]

### Secondary (MEDIUM confidence)
- None. [VERIFIED: research scope 2026-04-05]

### Tertiary (LOW confidence)
- None. [VERIFIED: research scope 2026-04-05]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - derived from local pyproject config and live `uv` environment imports. [VERIFIED: apps/api/pyproject.toml][VERIFIED: runtime import versions 2026-04-05]
- Architecture: HIGH - derived from mounted app wiring, dependency modules, and shared fixtures. [VERIFIED: apps/api/main_v2.py][VERIFIED: apps/api/tests/platform/fixtures.py]
- Pitfalls: HIGH - derived from direct code/test mismatches and verified targeted pytest runs. [VERIFIED: apps/api/middleware/logging.py][VERIFIED: apps/api/tests/unit/test_middleware_logging.py][VERIFIED: targeted pytest runs 2026-04-05]

**Research date:** 2026-04-05 [VERIFIED: this file]
**Valid until:** 2026-05-05 for repo-local planning unless Phase 01 code lands earlier. [ASSUMED]

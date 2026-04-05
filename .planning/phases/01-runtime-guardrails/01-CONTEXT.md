# Phase 1: Runtime Guardrails - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

이 phase는 `apps/api`의 현재 FastAPI 런타임에서 degraded health, request logging, auth/policy 경계를 하나의 신뢰 가능한 계약으로 고정한다. 범위는 `HEALTH-01`, `HEALTH-02`, `HEALTH-03`에 직접 연결되는 런타임 코드와 이를 증명하는 테스트까지이며, job runner 재설계나 schema truth 정리는 다음 phase로 넘긴다.

</domain>

<decisions>
## Implementation Decisions

### Health / Degraded Contract
- **D-01:** Redis는 `health/detailed` 경로에서 optional dependency로 취급한다. Redis 미초기화, 연결 실패, `ping()` 실패가 있어도 `/health/detailed`는 항상 HTTP 200을 반환한다.
- **D-02:** 상세 헬스 응답의 overall `status`는 DB, Redis, background task 상태를 종합해 계산하되, Redis 문제는 `degraded`로 표현하고 요청 자체를 500으로 실패시키지 않는다.
- **D-03:** Redis 컴포넌트 상태는 단순 boolean이 아니라 `healthy` / `unavailable` / `error`처럼 원인을 구분할 수 있는 방향으로 정리한다. fake나 잘못 주입된 객체를 `healthy`로 오인하는 현재 동작은 Phase 1에서 제거한다.

### Logging Contract
- **D-04:** `RequestLoggingMiddleware`를 canonical request logging 경로로 삼고, 현재 `LoggingMiddleware`가 가진 request id 부여, 민감정보 마스킹, start/complete/error 이벤트 책임을 여기에 흡수한다.
- **D-05:** 운영 기본 로그는 구조화된 `request_started` / `request_completed` / `request_failed` 이벤트를 유지하고, `X-Request-ID`는 하나의 middleware 경로에서 생성/전파한다.
- **D-06:** 요청 바디 로깅은 작은 JSON body에 한해 debug 레벨에서만 허용하고, 헤더/쿼리/body redaction 규칙은 공통 마스킹 헬퍼 하나로 통일한다.

### Authentication / Policy Boundary
- **D-07:** router 및 policy 경계의 canonical caller 타입은 `AuthenticatedPrincipal`로 통일한다. `APIKey` ORM은 credential lookup과 persistence update 단계 내부에서만 사용한다.
- **D-08:** `require_principal()` / `require_action()` 체인을 public dependency path로 간주하고, planner는 `require_api_key_record()`를 외부 계약처럼 확장하지 않는다.
- **D-09:** Usage accounting은 principal 기반 예약/커밋 seam을 유지하되, raw key hashing 같은 저장 방식 변경은 이 phase 범위에 넣지 않는다. 이번 phase의 목표는 type contract 통일과 request path 신뢰성 회복이다.

### the agent's Discretion
- Phase 1 구현에는 runtime code 수정과 이를 증명하는 unit/integration test 정리가 포함될 수 있다.
- broader docs truth cleanup, durable queue 논의, schema baseline 재정의는 이 phase에서 새 scope로 끌어오지 않는다.
- request id를 logging middleware가 소유할지 shared helper가 소유할지는 planner가 정하되, 최종 관찰 가능한 계약은 single source of truth여야 한다.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project / Phase Contract
- `.planning/PROJECT.md` — current project scope, non-negotiable constraints, brownfield context
- `.planning/REQUIREMENTS.md` — `HEALTH-01`, `HEALTH-02`, `HEALTH-03` acceptance criteria
- `.planning/ROADMAP.md` — Phase 1 goal, dependencies, and success criteria
- `.planning/STATE.md` — current execution position and active blockers

### Remediation Baseline
- `docs/plans/2026-03-19-architecture-remediation-execplan.md` — current stabilization direction, especially health/logging/auth mismatch notes and rollout ordering

### Codebase Maps
- `.planning/codebase/ARCHITECTURE.md` — runtime layer boundaries and health/auth/logging integration points
- `.planning/codebase/CONCERNS.md` — known runtime, security, and observability issues relevant to Phase 1
- `.planning/codebase/CONVENTIONS.md` — logging, error handling, and auth conventions already present in the repo
- `.planning/codebase/TESTING.md` — existing fake Redis, request logging tests, and integration harness patterns

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `apps/api/bootstrap/runtime.py:ObservabilityFacade` — already centralizes health snapshot rendering and is the natural seam for degraded component reporting
- `apps/api/routers/health.py:get_optional_redis()` and `apps/api/infrastructure/redis_client.py:check_redis_connection()` — existing starting points for optional Redis health behavior
- `apps/api/middleware/logging.py:_mask_sensitive_fields()` and `_mask_sensitive_value()` — current redaction helpers to preserve while canonicalizing logging
- `apps/api/middleware/policy_accounting.py` — already consumes `request.state.request_id` and `usage_reservation`, so request-id ownership needs to stay compatible with this seam
- `apps/api/dependencies/auth.py:require_principal()` and `require_action()` — existing principal-first dependency chain to reinforce instead of replace

### Established Patterns
- Redis failures are generally handled fail-open in runtime code, especially in `apps/api/main_v2.py`, `apps/api/infrastructure/redis_client.py`, and `apps/api/middleware/rate_limit.py`
- `structlog` with key-value fields is the preferred API logging style, even though some older paths still mix f-strings
- API routes already depend on `AuthenticatedPrincipal` for policy-protected endpoints, so Phase 1 should align the rest of the auth path to that contract rather than reintroduce `APIKey` at the router boundary
- tests rely on `FakeRedis` and `ASGITransport`-based app harnesses from `apps/api/tests/platform/fixtures.py`, so planner should reuse those instead of inventing new infrastructure doubles

### Integration Points
- `apps/api/routers/health.py` + `apps/api/bootstrap/runtime.py` — degraded health contract
- `apps/api/main_v2.py`, `apps/api/middleware/logging.py`, `apps/api/middleware/policy_accounting.py` — canonical request logging + request id propagation
- `apps/api/dependencies/auth.py`, `apps/api/policy/authentication.py`, `apps/api/policy/accounting.py`, `apps/api/policy/principal.py` — principal and accounting contract
- `apps/api/tests/unit/test_middleware_logging.py`, `apps/api/tests/unit/test_logging_redaction.py`, `apps/api/tests/unit/test_health_dynamic.py`, `apps/api/tests/integration/test_api_endpoints.py` — likely regression coverage entry points

</code_context>

<specifics>
## Specific Ideas

- `/health/detailed`는 Redis 장애를 "API 전체 장애"로 취급하지 말고 degraded 상태를 명시적으로 보여줘야 한다.
- logging은 middleware가 둘로 갈라진 상태를 유지하지 말고 하나의 canonical path로 합쳐야 한다.
- auth/policy 정리는 type contract 통일이 핵심이며, 보안 저장 방식 변경까지 한 번에 확장하지 않는다.

</specifics>

<deferred>
## Deferred Ideas

- API key hashing / public credential id 도입 — future security-focused phase
- durable queue 또는 orphaned job reconciliation — Phase 4 이후 execution platform work
- schema baseline unification and migration-only bootstrap — Phase 3
- broad docs truth cleanup outside runtime guardrails — Phase 6

</deferred>

---

*Phase: 01-runtime-guardrails*
*Context gathered: 2026-04-05*

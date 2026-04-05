---
phase: 03-unified-bootstrap
plan: 02
subsystem: database
tags: [fastapi, postgres, startup, pytest, lifespan]
requires:
  - phase: 03-unified-bootstrap
    provides: Explicit active manifest truth and legacy conflict markers from plan 01
provides:
  - Fail-closed startup guard for missing manifest rows, unexpected migration names, and mixed legacy state
  - Non-test lifespan rejection coverage for startup failures before request serving
affects: [phase-03-03, bootstrap-proof, ci-bootstrap-lane, operator-runtime]
tech-stack:
  added: []
  patterns: [fail-closed startup guard, direct lifespan rejection testing]
key-files:
  created:
    - apps/api/tests/integration/test_startup_manifest_rejection.py
  modified:
    - apps/api/infrastructure/database.py
    - apps/api/tests/unit/test_database_migration_guard.py
key-decisions:
  - "Manifest mismatch errors are split into missing rows and unexpected names so remediation stays operator-readable."
  - "Startup rejection is proved by opening the FastAPI lifespan context directly instead of relying on ASGI transport side effects."
patterns-established:
  - "Non-test startup must fail before serving whenever manifest history or legacy conflict markers are ambiguous."
  - "Integration tests for startup semantics should call `create_app()` and enter the app lifespan explicitly."
requirements-completed: [SCHEMA-02]
duration: 2 min
completed: 2026-04-05
---

# Phase 03 Plan 02: Unified Bootstrap Summary

**Non-test startup가 manifest drift와 mixed legacy state를 fail-closed로 거부하고, 그 예외가 FastAPI lifespan 밖으로 그대로 전파되도록 고정했다**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-05T08:22:40Z
- **Completed:** 2026-04-05T08:25:14Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- `require_migration_manifest()`가 missing manifest rows, unexpected migration names, mixed legacy/unified tables를 각각 다른 오류로 거부하도록 세분화했다.
- legacy-only table marker를 manifest helper에서 읽어 non-test startup이 mixed baseline을 fail-closed로 차단하게 만들었다.
- `create_app()`의 lifespan context를 직접 여는 통합 테스트를 추가해 startup 예외가 request serving 전에 전파됨을 증명했다.

## Task Commits

각 task는 원자적으로 커밋됐다:

1. **Task 1: Fail closed on mixed legacy and manifest mismatch state** - `3381138` (fix)
2. **Task 2: Prove FastAPI lifespan startup stops on manifest guard failures** - `af0722f` (test)

**Plan metadata:** SUMMARY는 별도 docs 커밋으로 분리한다.

## Files Created/Modified
- `apps/api/infrastructure/database.py` - manifest row와 legacy conflict table을 함께 검사하는 fail-closed startup guard를 제공한다.
- `apps/api/tests/unit/test_database_migration_guard.py` - missing row, unexpected row, mixed state, missing history 분기 커버리지를 추가했다.
- `apps/api/tests/integration/test_startup_manifest_rejection.py` - non-test `create_app()` lifespan에서 startup rejection이 request 전에 전파되는지를 검증한다.

## Decisions Made
- startup guard는 ambiguous schema 상태를 한 덩어리 mismatch로 숨기지 않고 operator remediation이 가능한 메시지로 분리한다.
- lifespan rejection 테스트는 `AsyncClient` 요청 대신 `app.router.lifespan_context(app)`를 직접 사용해 startup precondition을 명시적으로 검증한다.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ASGI transport was not exercising startup the way this test needed**
- **Found during:** Task 2 verification
- **Issue:** 초기 구현은 `ASGITransport` 요청 경로로 startup failure 전파를 검증하려 했지만, 이 코드베이스에서는 그 경로가 기대한 방식으로 lifespan raise를 관찰하지 못했다.
- **Fix:** `create_app()`로 만든 앱의 `lifespan_context`를 직접 열어 request serving 전 startup failure를 검증하도록 테스트를 바꿨다.
- **Files modified:** `apps/api/tests/integration/test_startup_manifest_rejection.py`
- **Verification:** `cd apps/api && uv run pytest -q tests/integration/test_startup_manifest_rejection.py -o addopts=''`
- **Committed in:** `af0722f`

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** 검증 경로가 더 직접적이고 요구사항과 더 정확히 맞아졌으며 scope creep는 없다.

## Issues Encountered

- 없음. startup failure semantics는 `lifespan_context` 직접 진입으로 안정적으로 고정됐다.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 03-03은 이제 fail-closed startup guard를 신뢰하고 fresh bootstrap proof와 CI lane 추가에 집중할 수 있다.
- mixed-state rejection과 missing history rejection이 이미 고정되어 있으므로 bootstrap proof는 manifest-first happy path만 증명하면 된다.

## Self-Check: PASSED

- Summary file exists at `.planning/phases/03-unified-bootstrap/03-unified-bootstrap-02-SUMMARY.md`
- Task commit `3381138` verified in git history
- Task commit `af0722f` verified in git history

---
*Phase: 03-unified-bootstrap*
*Completed: 2026-04-05*

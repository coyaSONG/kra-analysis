---
phase: 02-job-vocabulary
plan: 03
subsystem: api
tags: [fastapi, jobs, async-tasks, pytest, vocabulary]
requires:
  - phase: 02-job-vocabulary
    provides: Canonical public job type/status persistence and read-path cutover from plans 01 and 02
provides:
  - Async collection receipt-to-job-detail regression coverage that proves one externally visible `batch` job
  - Async task and statistics expectations aligned to canonical public type/status vocabulary
  - Service-level public type count guardrails that exclude internal dispatch aliases from persisted evidence
affects: [jobs-v2, async-collection, async-tasks, phase-04-runner-boundary]
tech-stack:
  added: []
  patterns: [receipt-follow-up contract proof, canonical public job statistics, shadow-field public mirroring]
key-files:
  created: []
  modified:
    - apps/api/services/job_service.py
    - apps/api/tests/unit/test_async_tasks.py
    - apps/api/tests/unit/test_job_service.py
    - apps/api/tests/integration/test_api_endpoints.py
key-decisions:
  - "Async collection proof stays on the existing receipt plus `/api/v2/jobs/{id}` follow-up pattern instead of introducing parent/child exposure."
  - "Job statistics and task-write regressions are keyed on canonical public types like `batch` and `collection`; internal dispatch names remain implementation detail only."
patterns-established:
  - "Validate async collection semantics through receipt follow-up assertions rather than transport-only checks."
  - "Use shared public job type/status constants in service statistics to keep contributor-facing evidence aligned with DTO vocabulary."
requirements-completed: [JOBS-01, JOBS-02]
duration: 10min
completed: 2026-04-05
---

# Phase 02 Plan 03: Job Vocabulary Summary

**`/api/v2/collection/async`의 receipt-follow-up 경로와 async task/statistics 회귀 기대치를 canonical `batch`/public lifecycle vocabulary로 끝까지 고정했다**

## Performance

- **Duration:** 10 min
- **Started:** 2026-04-05T06:52:00Z
- **Completed:** 2026-04-05T07:01:48Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- `/api/v2/collection/async` 응답의 `job_id`를 따라간 `/api/v2/jobs/{id}` 조회가 같은 `batch` job과 canonical status만 노출한다는 통합 회귀를 추가했다.
- async batch task 회귀 테스트에서 `job_kind_v2 == "batch_collect"` 같은 internal alias 기대를 제거하고 public `batch` shadow mirroring으로 맞췄다.
- `JobService.get_job_statistics()`가 canonical public type 집합만 집계하도록 상수화하고, unit test로 `batch_collect`/`collect_race` 같은 internal key가 통계에 나타나지 않음을 잠갔다.

## Task Commits

각 task는 원자적으로 커밋됐다:

1. **Task 1: Lock async collection submission to the canonical `batch` job semantics** - `d6129ce` (test)
2. **Task 2: Clean up async task writes and service statistics** - `2d097b4` (fix)

**Plan metadata:** `STATE.md`와 `ROADMAP.md`는 orchestrator 소유라 이번 실행에서 건드리지 않았고, SUMMARY.md는 별도 docs 커밋으로 분리한다.

## Files Created/Modified
- `apps/api/tests/integration/test_api_endpoints.py` - async collection receipt가 follow-up job detail에서 동일한 `batch` job과 canonical status만 보인다는 회귀를 추가했다.
- `apps/api/services/job_service.py` - statistics 집계가 public job type/status 목록만 사용하도록 상수화했다.
- `apps/api/tests/unit/test_async_tasks.py` - batch async task 완료 후 shadow type 기대치를 internal alias 대신 public `batch`로 고정했다.
- `apps/api/tests/unit/test_job_service.py` - statistics가 `collection`/`batch` 같은 public type만 집계하고 internal dispatch alias는 노출하지 않는다는 테스트를 추가했다.

## Decisions Made
- async collection의 외부 semantics는 기존 receipt transport를 유지하되, truth 검증은 `/api/v2/jobs/{id}` follow-up으로 잠근다.
- shadow/통계 회귀 테스트는 internal dispatch function name이 아니라 public persisted vocabulary를 검증 대상으로 삼는다.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Task 2 첫 커밋 시 `ruff format`이 `apps/api/tests/unit/test_job_service.py`를 자동 정리해 커밋이 한 번 중단됐다. 포맷 결과를 재검증한 뒤 같은 파일 집합만 다시 staging해 해결했다.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- async collection entrypoint, background task write path, statistics evidence가 모두 canonical public vocabulary를 기준으로 말하게 되었으므로 다음 phase는 runner boundary나 collection seam 분리 같은 구조 작업에 집중할 수 있다.
- shared artifact 갱신은 의도적으로 제외했으므로 orchestrator가 `STATE.md`/`ROADMAP.md` 동기화를 이어서 처리해야 한다.

## Self-Check: PASSED

- Summary file exists at `.planning/phases/02-job-vocabulary/02-job-vocabulary-03-SUMMARY.md`
- Task commit `d6129ce` verified in git history
- Task commit `2d097b4` verified in git history

---
*Phase: 02-job-vocabulary*
*Completed: 2026-04-05*

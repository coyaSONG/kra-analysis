---
phase: 02-job-vocabulary
plan: 02
subsystem: api
tags: [fastapi, jobs, migrations, pytest, vocabulary]
requires:
  - phase: 02-job-vocabulary
    provides: Canonical public job enums and persistence vocabulary from plan 01
provides:
  - Manifest-tracked backfill that rewrites legacy `running` and `retrying` rows to canonical `processing`
  - Jobs list/detail/cancel paths that read and serialize only canonical lifecycle values
  - Integration coverage that rejects removed public `running` filters and verifies `batch`/`queued` follow-up reads
affects: [jobs-v2, async-collection, phase-02-plan-03]
tech-stack:
  added: []
  patterns: [manifest-governed lifecycle backfill, canonical-only jobs read path]
key-files:
  created:
    - apps/api/migrations/006_canonical_job_status_backfill.sql
  modified:
    - apps/api/infrastructure/migration_manifest.py
    - apps/api/services/job_service.py
    - apps/api/routers/jobs_v2.py
    - apps/api/tests/unit/test_job_service.py
    - apps/api/tests/integration/test_jobs_v2_router_additional.py
    - apps/api/tests/integration/test_api_endpoints.py
key-decisions:
  - "Legacy lifecycle rows are normalized with a manifest-tracked SQL backfill before canonical-only reads ship."
  - "Jobs API query parsing and response serialization now reject or surface only canonical lifecycle values instead of silently normalizing `running`."
  - "Async collection follow-up reads continue to expose `batch` jobs with canonical queued/cancelled/processing lifecycle values."
patterns-established:
  - "Backfill stored job rows before removing compatibility reads from the public service/router path."
  - "Treat non-canonical lifecycle values at the router boundary as data bugs, not public compatibility inputs."
requirements-completed: [JOBS-02]
duration: 3min
completed: 2026-04-05
---

# Phase 02 Plan 02: Job Vocabulary Summary

**jobs API read/cancel 경로를 canonical lifecycle 값만 읽도록 전환하고 legacy status 행은 migration으로 `processing`에 정규화했다**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-05T15:51:23+09:00
- **Completed:** 2026-04-05T06:54:49Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- `006_canonical_job_status_backfill.sql`을 manifest에 연결해 legacy `running`/`retrying` job rows를 canonical `processing`으로 정규화했다.
- `JobService.list_jobs_with_total()`과 `jobs_v2` 라우터가 더 이상 legacy lifecycle 값을 보정하지 않고 canonical status만 필터링/직렬화하도록 정리했다.
- 통합 테스트를 canonical contract 기준으로 다시 작성해 `status=running`이 거부되고, active/cancelled/batch follow-up 응답이 `processing`/`cancelled`/`queued`만 노출되도록 고정했다.

## Task Commits

각 task는 다음 커밋 체인으로 남겼다:

1. **Task 1: Add migration-backed lifecycle normalization for legacy rows** - `9a82f3a` (test), `7d81d46` (feat)
2. **Task 2: Remove jobs API legacy read compatibility** - `19953e2` (feat)

**Plan metadata:** 이 실행에서는 커밋하지 않았다. `STATE.md`와 `ROADMAP.md`는 orchestrator 소유라 의도적으로 건드리지 않았다.

## Files Created/Modified
- `apps/api/migrations/006_canonical_job_status_backfill.sql` - legacy lifecycle rows를 canonical `processing`으로 일괄 정규화한다.
- `apps/api/infrastructure/migration_manifest.py` - unified migration chain head에 `006_canonical_job_status_backfill.sql`을 추가했다.
- `apps/api/services/job_service.py` - jobs list/status path가 canonical lifecycle 값만 필터링하고 반환하도록 정리했다.
- `apps/api/routers/jobs_v2.py` - router serialization이 legacy lifecycle normalization 없이 DTO enum만 통과시키도록 바꿨다.
- `apps/api/tests/unit/test_job_service.py` - manifest head가 canonical status backfill migration을 가리키는지 검증하는 RED/GREEN 테스트를 추가했다.
- `apps/api/tests/integration/test_jobs_v2_router_additional.py` - `processing`/`cancelled` canonical behavior와 removed `running` filter rejection을 검증하도록 재작성했다.
- `apps/api/tests/integration/test_api_endpoints.py` - jobs detail/cancel/async collection follow-up이 canonical status/type만 노출하는지 검증하도록 업데이트했다.

## Decisions Made
- Legacy compatibility는 read path에서 유지하지 않고, manifest-tracked migration으로 데이터를 먼저 정리한 뒤 canonical-only reads로 전환했다.
- Jobs router는 `running` 같은 제거된 vocabulary를 더 이상 public API 입력으로 허용하지 않는다.
- `/api/v2/collection/async` 이후 follow-up jobs read는 계속 `batch` type과 canonical queued lifecycle을 노출한다.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- 이전 실행에서 index에 staged 상태로 남아 있던 `.planning/phases/02-job-vocabulary/02-job-vocabulary-01-SUMMARY.md`가 RED 커밋 `9a82f3a`에 함께 포함됐다. 런타임 영향은 없었고, 이후 task 커밋은 다시 파일 단위 staging으로 정리했다.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- jobs API의 public read/cancel contract는 이제 canonical-only 상태이므로 다음 plan은 async task runtime write path와 남은 internal compatibility 흔적 정리에 집중할 수 있다.
- `STATE.md`와 `ROADMAP.md` 업데이트는 이번 실행에서 의도적으로 건너뛰었으므로 orchestrator가 shared artifact 동기화를 이어서 처리해야 한다.

## Self-Check: PASSED

- Summary file exists at `.planning/phases/02-job-vocabulary/02-job-vocabulary-02-SUMMARY.md`
- Task commit `9a82f3a` verified in git history
- Task commit `7d81d46` verified in git history
- Task commit `19953e2` verified in git history

---
*Phase: 02-job-vocabulary*
*Completed: 2026-04-05*

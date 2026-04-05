---
phase: 03-unified-bootstrap
plan: 03
subsystem: testing
tags: [postgres, pytest, ci, migrations, bootstrap]
requires:
  - phase: 03-unified-bootstrap
    provides: Fail-closed startup guard from plan 02
provides:
  - Disposable Postgres bootstrap fixture wired to the manifest migration runner
  - Integration proof that a fresh DB boots through the unified chain and then passes non-test startup
  - CI bootstrap verification lane that keeps the proof and startup rejection checks running continuously
affects: [phase-03-04, operator-bootstrap, ci, schema-bootstrap]
tech-stack:
  added: []
  patterns: [disposable bootstrap database fixture, direct migration-runner proof, focused CI bootstrap lane]
key-files:
  created:
    - apps/api/tests/integration/test_bootstrap_manifest.py
  modified:
    - apps/api/tests/platform/fixtures.py
    - apps/api/tests/conftest.py
    - .github/workflows/ci.yml
key-decisions:
  - "Bootstrap proof uses a disposable Postgres database and the checked-in migration runner instead of SQLite fixtures."
  - "The bootstrap fixture provisions missing Supabase-style roles only inside the disposable test cluster so historical migration checksums stay untouched."
patterns-established:
  - "Use dedicated Postgres fixtures for production-path bootstrap claims; keep `Base.metadata.create_all()` confined to fast SQLite tests."
  - "Encode non-test bootstrap proof as a focused CI step instead of broadening existing integration jobs."
requirements-completed: [SCHEMA-01, SCHEMA-02]
duration: 3 min
completed: 2026-04-05
---

# Phase 03 Plan 03: Unified Bootstrap Summary

**Disposable Postgres bootstrap proof와 non-test CI verification lane을 추가해 unified migration chain이 실제 fresh DB bootstrap 경로로 작동함을 증명했다**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-05T08:27:40Z
- **Completed:** 2026-04-05T08:31:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- `tests/platform/fixtures.py`에 disposable Postgres DB를 만들고 `scripts/apply_migrations.py`를 직접 실행하는 bootstrap-proof fixture를 추가했다.
- `tests/integration/test_bootstrap_manifest.py`가 empty DB -> manifest migration -> non-test startup success까지 하나의 proof로 검증하게 만들었다.
- `.github/workflows/ci.yml`에 bootstrap manifest verification step을 추가해 non-test startup rejection과 fresh bootstrap proof를 CI에서 계속 확인하게 했다.

## Task Commits

각 task는 원자적으로 커밋됐다:

1. **Task 1: Add a migration-first fresh-bootstrap proof harness** - `0186d8b` (test)
2. **Task 2: Enforce non-test bootstrap proof in CI** - `5083004` (ci)

**Plan metadata:** SUMMARY는 별도 docs 커밋으로 분리한다.

## Files Created/Modified
- `apps/api/tests/platform/fixtures.py` - disposable Postgres DB 생성, cluster role 보강, manifest migration 적용 helper를 제공한다.
- `apps/api/tests/integration/test_bootstrap_manifest.py` - fresh DB에서 `schema_migrations`와 unified tables가 생성되고 non-test startup이 성공하는지를 검증한다.
- `apps/api/tests/conftest.py` - bootstrap proof fixture를 pytest가 인식하도록 export를 추가했다.
- `.github/workflows/ci.yml` - CI postgres service 위에서 non-test bootstrap verification step을 실행한다.

## Decisions Made
- historical migration SQL은 checksum 안정성을 위해 수정하지 않고, 테스트 cluster에서만 필요한 Supabase role을 임시 생성해 plain Postgres bootstrap proof를 성립시킨다.
- bootstrap proof CI는 기존 integration job을 재정의하지 않고 별도 focused step으로 유지한다.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Plain Postgres lacked Supabase roles referenced by the migration chain**
- **Found during:** Task 1 verification
- **Issue:** `001_unified_schema.sql`과 `003_add_race_odds.sql`이 `service_role`/`authenticated` 정책을 만들면서 disposable Postgres DB에서 즉시 실패했다.
- **Fix:** historical migration 파일은 건드리지 않고, bootstrap fixture가 disposable cluster에서 필요한 role만 임시 생성/정리하도록 만들었다.
- **Files modified:** `apps/api/tests/platform/fixtures.py`
- **Verification:** `cd apps/api && uv run pytest -q tests/integration/test_bootstrap_manifest.py -o addopts=''`
- **Committed in:** `0186d8b`

**2. [Rule 3 - Blocking] New bootstrap fixture needed explicit pytest export**
- **Found during:** Task 1 verification
- **Issue:** `tests/conftest.py`가 새 fixture를 re-export하지 않아 integration test가 fixture를 찾지 못했다.
- **Fix:** `bootstrap_proof_database`를 conftest import 목록에 추가했다.
- **Files modified:** `apps/api/tests/conftest.py`
- **Verification:** `cd apps/api && uv run pytest -q tests/platform tests/integration/test_bootstrap_manifest.py -o addopts='' -k 'bootstrap or migration'`
- **Committed in:** `0186d8b`

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** proof 경로가 로컬/CI plain Postgres에서도 재현 가능해졌고 migration checksum은 보존됐다.

## Issues Encountered

- 없음. bootstrap proof와 CI lane 모두 계획 범위 안에서 해결됐다.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- operator entrypoint와 문서는 이제 실제 proof command와 same-source verification path만 가리키면 된다.
- CI에 bootstrap lane이 생겼으므로 03-04 문서는 코드/테스트 명령과 같은 truth를 그대로 재사용하면 된다.

## Self-Check: PASSED

- Summary file exists at `.planning/phases/03-unified-bootstrap/03-unified-bootstrap-03-SUMMARY.md`
- Task commit `0186d8b` verified in git history
- Task commit `5083004` verified in git history

---
*Phase: 03-unified-bootstrap*
*Completed: 2026-04-05*

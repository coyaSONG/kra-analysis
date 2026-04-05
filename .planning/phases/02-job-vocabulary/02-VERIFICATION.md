---
phase: 02-job-vocabulary
verified: 2026-04-05T07:13:57Z
status: passed
score: 6/6 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 5/6
  gaps_closed:
    - "Client can retrieve job status and cancellation responses that use the same canonical vocabulary shown at job creation."
  gaps_remaining: []
  regressions: []
---

# Phase 2: Job Vocabulary Verification Report

**Phase Goal:** Client가 job 생성, 상태 조회, 취소 응답에서 같은 작업 타입과 상태 vocabulary를 본다.
**Verified:** 2026-04-05T07:13:57Z
**Status:** passed
**Re-verification:** Yes — after gap closure

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Client can submit async collection jobs using one canonical job type set accepted by request DTOs and dispatch logic. | ✓ VERIFIED | `apps/api/models/job_dto.py`와 `apps/api/models/database_models.py`의 `JobType`은 canonical 값만 노출하고, `apps/api/services/job_contract.py`의 `normalize_job_kind()`가 internal alias를 `collection`/`batch`로 정규화한다. `apps/api/services/kra_collection_module.py`는 `job_type="batch"`로 job을 생성한다. |
| 2 | Contributor can inspect a submitted job in the database and API responses without translating between parallel alias names. | ✓ VERIFIED | `apps/api/services/job_contract.py`의 `apply_job_shadow_fields()`가 `job_kind_v2`/`lifecycle_state_v2`를 canonical vocabulary로 미러링하고, router DTO 직렬화는 `job.type`/`job.status`만 public truth로 사용한다. |
| 3 | Client can retrieve job status and cancellation responses that use the same canonical vocabulary shown at job creation. | ✓ VERIFIED | `apps/api/models/job_dto.py`에 `JobCancelResponse`가 정의되어 있고, `apps/api/routers/jobs_v2.py`의 cancel route는 `response_model=JobCancelResponse`로 선언된 뒤 취소된 job을 재조회해 `job=_to_job_dto(cancelled_job)`를 반환한다. Integration tests는 cancel 응답의 `job.type == "collection"`과 `job.status == "cancelled"`를 검증한다. |
| 4 | Canonical-only reads do not depend on `lifecycle_state_v2` fallback logic. | ✓ VERIFIED | `apps/api/services/job_service.py`의 `list_jobs_with_total()`은 `Job.status`와 `Job.type`만으로 필터링하고, `apps/api/routers/jobs_v2.py`는 canonical enum DTO로만 query/response를 처리한다. |
| 5 | Legacy `running` and `retrying` rows are normalized before canonical-only reads ship. | ✓ VERIFIED | `apps/api/migrations/006_canonical_job_status_backfill.sql`이 `running`/`retrying`를 `processing`으로 backfill하고, `apps/api/infrastructure/migration_manifest.py`가 이를 active migration head에 포함한다. |
| 6 | One `/api/v2/collection/async` request produces one externally visible `batch` job, and receipt follow-up uses the same canonical vocabulary. | ✓ VERIFIED | `apps/api/services/kra_collection_module.py`의 `submit_batch_collect()`는 canonical `batch` job을 생성하고, `apps/api/tests/integration/test_api_endpoints.py`는 receipt의 `job_id`를 따라 `/api/v2/jobs/{id}` 조회 시 `type == "batch"`와 canonical lifecycle만 노출됨을 확인한다. |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `apps/api/services/job_contract.py` | public vocabulary and dispatch alias separation | ✓ VERIFIED | Public type/status normalization과 internal dispatch alias translation이 명확히 분리되어 있다. |
| `apps/api/models/job_dto.py` | public DTO enums limited to canonical values | ✓ VERIFIED | `JobType`, `JobStatus`, `JobCancelResponse`가 canonical 공개 계약을 정의한다. |
| `apps/api/models/database_models.py` | ORM enums align with public vocabulary | ✓ VERIFIED | ORM `JobType`/`JobStatus`가 canonical 값만 포함한다. |
| `apps/api/tests/unit/test_job_contract.py` | regression coverage for canonical/public separation | ✓ VERIFIED | alias 입력이 canonical persisted/shadow 값으로 수렴함을 검증한다. |
| `apps/api/migrations/006_canonical_job_status_backfill.sql` | legacy lifecycle normalization | ✓ VERIFIED | legacy lifecycle row를 `processing`으로 정규화한다. |
| `apps/api/services/job_service.py` | canonical create/read/filter/cancel logic | ✓ VERIFIED | create/read/filter/cancel이 canonical vocabulary를 유지하고 cancel은 router가 DTO 재직렬화할 수 있도록 일관된 persisted state를 남긴다. |
| `apps/api/routers/jobs_v2.py` | public query parsing and serialization limited to canonical status vocabulary | ✓ VERIFIED | list/detail/cancel 모두 canonical DTO를 사용하며 cancel도 `JobCancelResponse`를 반환한다. |
| `apps/api/tests/integration/test_jobs_v2_router_additional.py` | canonical list/detail/cancel regression coverage | ✓ VERIFIED | `status=running` 거부, detail canonical status, cancel 응답의 canonical type/status를 검증한다. |
| `apps/api/services/kra_collection_module.py` | async receipt semantics create canonical `batch` job | ✓ VERIFIED | async receipt가 one-request-one-`batch` semantics를 유지한다. |
| `apps/api/tasks/async_tasks.py` | background task writes preserve canonical vocabulary | ✓ VERIFIED | `_update_job_status()`가 persisted status와 shadow lifecycle을 canonical 값으로 갱신한다. |
| `apps/api/tests/unit/test_async_tasks.py` | async task write regression coverage | ✓ VERIFIED | task execution 후 `job_kind_v2`/`lifecycle_state_v2`가 canonical 값인지 검증한다. |
| `apps/api/tests/integration/test_api_endpoints.py` | end-to-end receipt-to-job-detail vocabulary proof | ✓ VERIFIED | async collection follow-up과 cancel 응답이 canonical vocabulary를 유지함을 검증한다. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `apps/api/services/job_service.py` | `apps/api/services/job_contract.py` | `normalize_dispatch_action(...)` | ✓ WIRED | service create/dispatch/shadow write 경로가 contract helpers를 일관되게 사용한다. |
| `apps/api/models/job_dto.py` | `apps/api/routers/jobs_v2.py` | `JobStatus` / `JobType` query-response enums | ✓ WIRED | router query parsing, detail serialization, cancel serialization 모두 DTO enums를 사용한다. |
| `apps/api/infrastructure/migration_manifest.py` | `apps/api/migrations/006_canonical_job_status_backfill.sql` | `ACTIVE_MIGRATIONS` | ✓ WIRED | canonical lifecycle backfill이 active migration chain에 포함되어 있다. |
| `apps/api/routers/jobs_v2.py` | `apps/api/services/job_service.py` | `list_jobs_with_total` / `cancel_job` | ✓ WIRED | router가 service를 호출한 뒤 cancel 시 재조회한 canonical job row를 `JobCancelResponse`로 직렬화한다. |
| `apps/api/services/kra_collection_module.py` | `apps/api/services/job_service.py` | `create_job(...)` / `start_job(...)` | ✓ WIRED | async collection receipt는 canonical `batch` job 생성과 시작을 service seam에 위임한다. |
| `apps/api/tasks/async_tasks.py` | `apps/api/services/job_contract.py` | `apply_job_shadow_fields(...)` | ✓ WIRED | background task status write가 canonical shadow mirroring을 사용한다. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| --- | --- | --- | --- | --- |
| `apps/api/services/job_service.py` | `job.type`, `job.status` | SQLAlchemy `Job` row writes/reads in `create_job()`, `list_jobs_with_total()`, `cancel_job()` | Yes | ✓ FLOWING |
| `apps/api/routers/jobs_v2.py` | `dto_jobs`, `dto_job`, `cancelled_job` | `JobService.list_jobs_with_total()`, `JobService.get_job()`, `JobService.cancel_job()` 후 재조회 | Yes | ✓ FLOWING |
| `apps/api/services/kra_collection_module.py` | `receipt.job_id` plus persisted `batch` job | `JobService.create_job()` + `start_job()` | Yes | ✓ FLOWING |
| `apps/api/tasks/async_tasks.py` | `job.status`, `job.job_kind_v2`, `job.lifecycle_state_v2` | `_update_job_status()`가 실제 `Job` row를 조회 후 mutate | Yes | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Phase 02 regression subset passes | `cd apps/api && uv run pytest -q tests/unit/test_job_contract.py tests/unit/test_job_dispatch.py tests/unit/test_job_service.py tests/unit/test_async_tasks.py tests/integration/test_jobs_v2_router_additional.py tests/integration/test_api_endpoints.py -o addopts='' -k 'jobs or cancel_job or get_job_detail or async_collect or statistics or batch_collect'` | `23 passed, 40 deselected, 11 warnings in 0.72s` | ✓ PASS |
| Cancel response exposes canonical vocabulary directly | `rg -n "response_model=JobCancelResponse|return JobCancelResponse|job=_to_job_dto\\(cancelled_job\\)|class JobCancelResponse|job: Job" apps/api/routers/jobs_v2.py apps/api/models/job_dto.py` | Route and DTO both declare a job-bearing cancel response contract | ✓ PASS |
| Cancel integration tests assert canonical response body | `rg -n "status\\\"\\] == \\\"cancelled\\\"|type\\\"\\] == \\\"collection\\\"|message\\\"\\] == \\\"Job cancelled successfully\\\"" apps/api/tests/integration/test_jobs_v2_router_additional.py apps/api/tests/integration/test_api_endpoints.py` | Both integration suites assert cancel response includes canonical `job.type` and `job.status` | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| `JOBS-01` | `02-01`, `02-03` | Client can submit async collection jobs using one canonical job type vocabulary accepted by request DTOs, persisted rows, and dispatch logic. | ✓ SATISFIED | DTO/ORM enums, `normalize_job_kind()`, `create_job()`, and `/api/v2/collection/async` follow-up coverage all use canonical `collection`/`batch` vocabulary. |
| `JOBS-02` | `02-02`, `02-03` | Client can retrieve job status and cancellation responses that use the same canonical vocabulary as job creation. | ✓ SATISFIED | list/detail/cancel routes serialize canonical status/type, and cancel now returns `JobCancelResponse` with a canonical `job` payload. |

Phase 02 plan frontmatter declared only `JOBS-01` and `JOBS-02`, and both map cleanly to `.planning/REQUIREMENTS.md`. REQUIREMENTS.md에는 Phase 2에 대한 추가 orphaned requirement ID가 없다.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| None | - | No TODO/stub/placeholder/blocker patterns detected in phase-owned files | ℹ️ Info | 구현은 실체가 있고, 이전 gap도 메시지-only cancel 응답에서 canonical DTO 응답으로 실제 교체됐다. |

### Human Verification Required

None.

### Gaps Summary

이전 검증의 유일한 gap은 cancel 응답이 canonical vocabulary를 직접 노출하지 않는 점이었다. 현재 코드에서는 `JobCancelResponse`가 추가되었고, cancel route가 취소 직후 job row를 재조회해 canonical `job.type`/`job.status`를 응답 본문에 포함한다. 생성, 조회, 취소, async follow-up, persisted/shadow fields, migration-backed legacy normalization까지 모두 같은 vocabulary를 사용함이 코드와 테스트로 확인되므로 Phase 02 goal은 달성됐다.

---

_Verified: 2026-04-05T07:13:57Z_  
_Verifier: Claude (gsd-verifier)_

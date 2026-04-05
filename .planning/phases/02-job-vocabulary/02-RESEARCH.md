# Phase 02: Job Vocabulary - Research

**Researched:** 2026-04-05 [VERIFIED: .planning/phases/02-job-vocabulary/02-CONTEXT.md]  
**Domain:** async job type/status vocabulary consolidation across DTO, ORM, service, router, and async task write paths [VERIFIED: .planning/phases/02-job-vocabulary/02-CONTEXT.md][VERIFIED: apps/api/models/job_dto.py][VERIFIED: apps/api/models/database_models.py][VERIFIED: apps/api/services/job_service.py]  
**Confidence:** HIGH [VERIFIED: repo code reads 2026-04-05]

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions [VERIFIED: .planning/phases/02-job-vocabulary/02-CONTEXT.md]
- **D-01:** 외부 canonical job type은 제품/API vocabulary로 유지한다. public surface는 `collection`, `batch`, `enrichment`, `analysis`, `prediction`, `improvement`를 사용해야 한다.
- **D-02:** `collect_race`, `batch_collect`, `enrich_race`, `full_pipeline` 같은 실행 단위 이름은 internal dispatch 전용이다. jobs API와 public filter surface에 1급 vocabulary로 남기지 않는다.
- **D-03:** 외부 canonical lifecycle status는 `pending`, `queued`, `processing`, `completed`, `failed`, `cancelled`로 수렴한다.
- **D-04:** `running`, `retrying`은 internal/transitional alias로만 취급한다. final public contract에는 남기지 않는다.
- **D-05:** `/api/v2/collection/async` 1회 호출은 외부에서 `batch` job 1개로 보이는 것이 canonical semantics다.
- **D-06:** race별 collect 실행은 internal detail이며 이번 phase에서 parent/child public job graph를 만들지 않는다.
- **D-07:** legacy dual-read fallback은 이번 phase에서 제거한다. final jobs read path는 canonical-only여야 한다.
- **D-08:** canonical-only cutover가 shadow field 승격을 뜻하는 것은 아니다. external canonical은 계속 제품/API vocabulary여야 한다.

### Claude's Discretion [VERIFIED: .planning/phases/02-job-vocabulary/02-CONTEXT.md]
- cutover 순서는 planner가 정하되, 최종 관찰 가능한 truth는 `Job.type`/`Job.status` 중심의 external contract여야 한다.
- `JOBS-03` 범위의 runner boundary 재설계는 이번 phase에 새 capability로 끌어오지 않는다.
- auth/ownership/pagination은 Phase 1 결정을 유지한다.

### Deferred Ideas (OUT OF SCOPE) [VERIFIED: .planning/phases/02-job-vocabulary/02-CONTEXT.md]
- durable queue, orphaned job replay, explicit worker boundary
- parent/child job graph public exposure
- deeper race-processing workflow refactor
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| JOBS-01 | Client can submit async collection jobs using one canonical job type vocabulary accepted by request DTOs, persisted rows, and dispatch logic. [VERIFIED: .planning/REQUIREMENTS.md] | Keep `jobs.type` as public type source of truth, map `batch -> BATCH_COLLECT` and `collection -> COLLECT_RACE` only inside dispatch normalization, and stop persisting internal alias names as if they were canonical. [VERIFIED: apps/api/models/database_models.py][VERIFIED: apps/api/services/job_contract.py][VERIFIED: apps/api/services/kra_collection_module.py] |
| JOBS-02 | Client can retrieve job status and cancellation responses that use the same canonical vocabulary as job creation. [VERIFIED: .planning/REQUIREMENTS.md] | Remove `running`/`retrying` from public DTO/filter enums, backfill legacy rows to `processing`, and make jobs read/cancel paths depend on canonical columns instead of `lifecycle_state_v2` fallback logic. [VERIFIED: apps/api/models/job_dto.py][VERIFIED: apps/api/services/job_service.py][VERIFIED: apps/api/routers/jobs_v2.py] |
</phase_requirements>

## Project Constraints

- Active runtime is `apps/api`; changes must preserve existing collection and jobs endpoint compatibility beyond the vocabulary cleanup. [VERIFIED: .planning/PROJECT.md][VERIFIED: CLAUDE.md]
- The repo already has a canonical migration manifest; if this phase needs a data backfill migration, it must join that manifest instead of introducing ad hoc SQL execution. [VERIFIED: apps/api/infrastructure/migration_manifest.py][VERIFIED: apps/api/scripts/apply_migrations.py]
- Phase 3 owns unified bootstrap and manifest enforcement; Phase 2 should only introduce the minimal migration/backfill needed for truthful job vocabulary data. [VERIFIED: .planning/ROADMAP.md]

## Summary

- Public type/status truth already exists in the schema shape: `models/job_dto.py` and `models/database_models.py` expose `collection|batch|...`, while dispatch drift is concentrated in `services/job_contract.py` and tests that still assert internal aliases. [VERIFIED: apps/api/models/job_dto.py][VERIFIED: apps/api/models/database_models.py][VERIFIED: apps/api/services/job_contract.py]
- The biggest remaining lie is on the read path, not the create path. `CollectionJobs.submit_batch_collect()` already persists `job_type="batch"`, but `list_jobs_with_total()` still dual-reads `lifecycle_state_v2` and accepts `running` filters. [VERIFIED: apps/api/services/kra_collection_module.py][VERIFIED: apps/api/services/job_service.py]
- `job_kind_v2` and `lifecycle_state_v2` are compatibility columns introduced by rollout work, but current tests still treat them as canonical evidence. Phase 2 should demote them to non-public internals or mirrored compatibility fields, not the source of truth. [VERIFIED: docs/plans/2026-03-19-architecture-rollout-execplan.md][VERIFIED: apps/api/tests/unit/test_job_contract.py][VERIFIED: apps/api/tests/unit/test_async_tasks.py]
- The safest cutover is: keep `jobs.type` and `jobs.status` as the only public read/write truth, keep internal dispatch mapping inside `normalize_dispatch_action()`, and backfill legacy `running|retrying` rows to `processing` before removing compatibility reads. [VERIFIED: apps/api/services/job_contract.py][VERIFIED: apps/api/services/job_service.py]

**Primary recommendation:** Plan this phase as three sequential slices: public vocabulary core cleanup, jobs API canonical-only read/cancel cutover with targeted migration/backfill, and async collection/task/runtime cleanup so batch submission and follow-up job reads stay truthful end-to-end. [VERIFIED: .planning/phases/02-job-vocabulary/02-CONTEXT.md][VERIFIED: docs/plans/2026-03-19-architecture-remediation-execplan.md]

## Recommended Cutover Strategy

### 1. Public truth stays on `jobs.type` and `jobs.status`
- `JobType` in DTO/ORM is already the user-facing set and should remain the persisted/public vocabulary. [VERIFIED: apps/api/models/job_dto.py][VERIFIED: apps/api/models/database_models.py]
- `normalize_dispatch_action()` should continue translating public types to internal actions, but `normalize_job_kind()` and shadow-field helpers should stop turning `batch` into `batch_collect` for persisted evidence. [VERIFIED: apps/api/services/job_contract.py]

### 2. Public lifecycle must shrink before read-compat is removed
- `JobStatus` currently still exposes `RUNNING` and `RETRYING` in both DTO and ORM. Those values keep OpenAPI/query params inconsistent with the locked external contract. [VERIFIED: apps/api/models/job_dto.py][VERIFIED: apps/api/models/database_models.py]
- `list_jobs_with_total()` currently uses `lifecycle_state_v2` plus legacy fallback to match `processing`. That logic must be deleted only after legacy rows are rewritten to canonical values. [VERIFIED: apps/api/services/job_service.py]

### 3. Minimal migration is enough; enum surgery is not required in this phase
- The repo now has manifest-driven migrations, so a small `006_*` migration can safely backfill `jobs.status IN ('running','retrying')` to `processing` and align compatibility columns if needed. [VERIFIED: apps/api/infrastructure/migration_manifest.py][VERIFIED: apps/api/scripts/apply_migrations.py]
- PostgreSQL enum-label deletion is avoidable here. The phase goal is truthful persisted rows and app contract, not aggressive storage-type surgery. Application code can reject old values once data is backfilled. [INFERENCE from current schema and phase scope]

### 4. `/collection/async` should prove the contract, not expand it
- `CollectionJobs.submit_batch_collect()` already creates `job_type="batch"` and starts the background task. The missing proof is regression coverage that the follow-up `/api/v2/jobs/{id}` response shows `type=batch` and canonical statuses only. [VERIFIED: apps/api/services/kra_collection_module.py][VERIFIED: apps/api/tests/integration/test_api_endpoints.py]
- The `accepted` submission receipt can stay as submission transport state; the job record exposed via jobs API must use canonical job vocabulary. [VERIFIED: apps/api/services/kra_collection_module.py][INFERENCE from current response model]

## Required Changes

### Public Vocabulary Core
- Remove `RUNNING` and `RETRYING` from `models/job_dto.JobStatus` so generated API docs and query parsing stop advertising them. [VERIFIED: apps/api/models/job_dto.py]
- Remove `RUNNING` and `RETRYING` from `models/database_models.JobStatus` and update tests/fixtures that still create those enum values directly. [VERIFIED: apps/api/models/database_models.py][VERIFIED: apps/api/tests/integration/test_jobs_v2_router_additional.py][VERIFIED: apps/api/tests/unit/test_job_service.py]
- Change `apply_job_shadow_fields()` so public rows mirror public type/status instead of persisting internal alias names like `batch_collect`. [VERIFIED: apps/api/services/job_contract.py][VERIFIED: apps/api/tests/unit/test_job_contract.py]

### Jobs API Cutover
- Delete `list_jobs_with_total()` dual-read logic on `lifecycle_state_v2` and `running` fallback; filter only on canonical `Job.status`. [VERIFIED: apps/api/services/job_service.py]
- Keep `_dto_job_status()` simple by rejecting non-canonical values at the model boundary instead of normalizing public legacy inputs forever. [VERIFIED: apps/api/routers/jobs_v2.py]
- Preserve cancel behavior but ensure tests and responses only reference canonical lifecycle values. [VERIFIED: apps/api/routers/jobs_v2.py][VERIFIED: apps/api/services/job_service.py]

### Async Runtime and Internal Cleanup
- Update `_update_job_status()` callers so persisted rows remain on canonical public lifecycle values across collect/batch/full-pipeline tasks. [VERIFIED: apps/api/tasks/async_tasks.py]
- Rewrite statistics and service-level tests that still count or assert `collect_race`, `batch_collect`, and `full_pipeline` as persisted job types. [VERIFIED: apps/api/services/job_service.py][VERIFIED: apps/api/tests/unit/test_job_dispatch.py][VERIFIED: apps/api/tests/unit/test_async_tasks.py]
- Add integration coverage from `/api/v2/collection/async` to `/api/v2/jobs/{id}` proving `batch` remains visible externally. [VERIFIED: apps/api/tests/integration/test_api_endpoints.py]

## Reusable Patterns

### Pattern 1: Public Enum at the Router Boundary
**What:** `jobs_v2.py` already converts SQLAlchemy rows into Pydantic DTOs using `JobType(...)` and `JobStatus(...)`. [VERIFIED: apps/api/routers/jobs_v2.py]  
**When to use:** Use this as the enforcement point for “public only” vocabulary. If a row cannot be represented by the DTO enum after Phase 2, that is a data bug, not something to silently normalize forever. [VERIFIED: apps/api/routers/jobs_v2.py][INFERENCE from D-07]

### Pattern 2: Internal Dispatch Translation Behind the Service
**What:** `JobService._dispatch_task()` already resolves execution behavior through `normalize_dispatch_action(job.type)`. [VERIFIED: apps/api/services/job_service.py][VERIFIED: apps/api/services/job_contract.py]  
**When to use:** Keep public job types stable and confine internal task naming to this translation seam rather than leaking it into ORM tests or API filters.

### Pattern 3: Manifest-Governed Data Backfill
**What:** migration application is now manifest-driven through `ACTIVE_MIGRATIONS` and `scripts/apply_migrations.py`. [VERIFIED: apps/api/infrastructure/migration_manifest.py][VERIFIED: apps/api/scripts/apply_migrations.py]  
**When to use:** If legacy rows must be normalized before canonical-only reads go live, add one small migration and test it instead of shipping an ad hoc startup rewrite.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Public job vocabulary | New second enum family for “API v3” while old enums stay alive. | Existing `JobType` / `JobStatus` as the single public vocabulary. | The repo already has DTO/ORM enums; drift comes from duplicate semantics, not missing types. |
| Dispatch selection | Router-level `if/elif` dispatch naming. | `normalize_dispatch_action()` in `services/job_contract.py`. | Internal execution names should stay service-local. |
| Legacy row cleanup | Startup-time silent coercion of every job row. | One manifest-tracked SQL migration plus targeted regression tests. | Phase 3 already established migration truth; reuse it. |
| API compatibility | Permanent dual-read on `lifecycle_state_v2`. | Canonical-only `Job.status` read path after backfill. | Locked decision D-07 explicitly rejects long-lived fallback logic. |

## Common Pitfalls

### Pitfall 1: Keeping `running` in Query Params While Claiming Canonical-Only
**What goes wrong:** OpenAPI and FastAPI query parsing still accept `status=running`, so the public contract never actually shrinks. [VERIFIED: apps/api/models/job_dto.py][VERIFIED: apps/api/routers/jobs_v2.py]  
**How to avoid:** remove those enum members and rewrite tests that currently send or assert `running`.

### Pitfall 2: Treating Shadow Fields as Public Evidence
**What goes wrong:** tests remain green while `job_kind_v2=batch_collect` contradicts `type=batch`, so contributors still see two truths in one row. [VERIFIED: apps/api/tests/unit/test_async_tasks.py][VERIFIED: apps/api/tests/unit/test_job_contract.py]  
**How to avoid:** either mirror public vocabulary into shadow fields or stop asserting on them for public jobs; never persist internal aliases as if they were canonical.

### Pitfall 3: Deleting Compatibility Reads Before Legacy Rows Are Fixed
**What goes wrong:** canonical-only `Job.status` reads miss preexisting `running` or `retrying` rows. [VERIFIED: apps/api/services/job_service.py][VERIFIED: docs/plans/2026-03-19-architecture-rollout-execplan.md]  
**How to avoid:** sequence the cutover behind a targeted backfill migration and explicit tests for post-migration behavior only.

### Pitfall 4: Letting Batch Submission Prove the Wrong Type
**What goes wrong:** `/collection/async` receipt succeeds, but later job detail still leaks internal vocabulary or stale status aliases. [VERIFIED: apps/api/tests/integration/test_api_endpoints.py][VERIFIED: apps/api/services/kra_collection_module.py]  
**How to avoid:** add one integration path that creates a batch job, follows its jobs endpoint, and asserts `type=batch` plus canonical lifecycle vocabulary.

## Key Insight

Phase 2 does not need a new job architecture. It needs to stop lying about which vocabulary is public and which one is internal. The existing public columns already provide the right anchor; the remaining work is deleting compatibility indirection once the stored data is safe to trust. [VERIFIED: apps/api/models/database_models.py][VERIFIED: apps/api/services/job_service.py][VERIFIED: .planning/phases/02-job-vocabulary/02-CONTEXT.md]

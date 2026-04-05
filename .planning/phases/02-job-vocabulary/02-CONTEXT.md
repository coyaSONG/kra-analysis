# Phase 2: Job Vocabulary - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

이 phase는 async job 생성, 상태 조회, 취소 응답이 DB, API, service, dispatch 경계에서 하나의 작업 vocabulary를 사용하도록 고정한다. 범위는 `JOBS-01`, `JOBS-02`에 직접 연결되는 job type/status 계약과 read/write 정규화 경로까지이며, durable queue 도입이나 race-processing workflow 재구성은 다음 phase로 넘긴다.

</domain>

<decisions>
## Implementation Decisions

### External Job Type Contract
- **D-01:** 외부 canonical job type은 제품/API vocabulary로 고정한다. `collection`, `batch`, `enrichment`, `analysis`, `prediction`, `improvement` 같은 도메인 용어가 API 응답, 요청 DTO, 조회 필터, 문서, DB의 사용자 관찰 경계에 남아야 한다.
- **D-02:** `collect_race`, `batch_collect`, `enrich_race`, `full_pipeline` 같은 실행 단위 이름은 내부 dispatch 전용 vocabulary로만 취급한다. planner는 이 용어들이 외부 jobs API 응답이나 public filter surface로 새로 노출되지 않도록 해야 한다.

### External Lifecycle Contract
- **D-03:** 외부 canonical lifecycle status는 `pending`, `queued`, `processing`, `completed`, `failed`, `cancelled`로 수렴한다.
- **D-04:** `running`과 `retrying`은 내부 alias 또는 transitional runtime signal로만 취급한다. final public contract에는 1급 상태로 남기지 않는다.

### Async Collection Semantics
- **D-05:** `/api/v2/collection/async` 한 번 호출은 외부에서 `batch` job 1개로 보이는 것이 canonical semantics다.
- **D-06:** race별 collect 실행은 내부 detail로만 취급한다. 이번 phase에서 parent/child job 모델을 public API에 추가하지 않는다.

### Cutover and Compatibility
- **D-07:** legacy dual-read fallback은 이번 phase에서 제거하는 방향으로 잠근다. planner는 final read path가 canonical-only가 되도록 설계해야 하며, legacy alias를 장기 운영 계약으로 남기지 않는다.
- **D-08:** 다만 canonical-only cutover의 의미는 "현재 shadow field를 그대로 public canonical로 승격"하는 것이 아니다. 외부 canonical은 위의 제품/API vocabulary를 따라야 하며, planner는 schema/read-path/backfill 전략을 연구해 이 조건을 만족하는 cutover 방식을 제안해야 한다.

### the agent's Discretion
- cutover를 schema migration, backfill, field repurposing, legacy column removal 중 어떤 순서로 구현할지는 planner가 정한다. 단, 최종 관찰 가능한 계약은 external product vocabulary와 canonical-only read다.
- `JOBS-03` 범위의 runner boundary 재설계나 parent/child execution graph 도입은 이 phase에 새 capability로 끌어오지 않는다.
- jobs API의 pagination, ownership, auth contract은 Phase 1 결정을 그대로 따른다.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project / Phase Contract
- `.planning/PROJECT.md` — 브라운필드 제약, 기존 jobs endpoint 호환성, 플랫폼 안정화 우선 원칙
- `.planning/REQUIREMENTS.md` — `JOBS-01`, `JOBS-02` acceptance criteria
- `.planning/ROADMAP.md` — Phase 2 goal, success criteria, 후속 Phase 4 runner boundary와의 관계
- `.planning/STATE.md` — 현재 Phase 2 진입 상태와 prior phase completion

### Prior Phase Context
- `.planning/phases/01-runtime-guardrails/01-CONTEXT.md` — Phase 1에서 확정된 auth/runtime contract, 기존 endpoint compatibility 원칙

### Remediation / Rollout Baseline
- `docs/plans/2026-03-19-architecture-remediation-execplan.md` — job vocabulary drift의 문제 정의와 Phase 2 scope 배경
- `docs/plans/2026-03-19-architecture-rollout-execplan.md` — `job_kind_v2` / `lifecycle_state_v2` shadow-field 도입 배경과 read-compat 단계 설명

### Codebase Maps
- `.planning/codebase/CONCERNS.md` — 분열된 job vocabulary와 in-process runner 리스크
- `.planning/codebase/CONVENTIONS.md` — compatibility field naming, DTO/ORM naming, API logging/auth conventions
- `.planning/codebase/STRUCTURE.md` — `routers/jobs_v2.py`, `services/job_service.py`, `services/job_contract.py`, `tasks/async_tasks.py` 소유 경계

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `apps/api/services/job_contract.py` — 현재 dispatch/lifecycle normalization seam. canonical vocabulary 정리의 첫 진입점이다.
- `apps/api/services/job_service.py` — job create/start/list/get/cancel path를 한 곳에서 통제하고 있어 Phase 2의 핵심 orchestration seam이다.
- `apps/api/routers/jobs_v2.py` — external jobs API type/status serialization과 filter surface를 고정하는 경계다.
- `apps/api/services/kra_collection_module.py:CollectionJobs.submit_batch_collect()` — `/collection/async`의 current async job semantics를 결정하는 entry point다.
- `apps/api/tasks/async_tasks.py::_update_job_status()` — async runtime이 DB status를 어떻게 쓰는지 정하는 write seam이다.

### Established Patterns
- 현재 repo는 dual-write/shadow-field로 vocabulary drift를 완화하고 있다. `job_kind_v2`, `lifecycle_state_v2`는 이미 읽기 호환과 테스트 자산에 깊게 연결돼 있다.
- jobs read path는 이미 일부 normalization을 수행한다. 특히 `running -> processing` read-compat이 integration test로 고정돼 있다.
- async collection path는 request-level receipt를 반환하고, client는 후속 `/api/v2/jobs/{id}` 조회로 상태를 본다. 이 receipt model을 parent/child graph 없이 유지하는 것이 현재 API pattern이다.

### Integration Points
- `apps/api/models/job_dto.py` — public type/status enum과 response shape
- `apps/api/models/database_models.py` — DB enum, shadow fields, 인덱스, persistence compatibility
- `apps/api/services/job_contract.py` — alias map, normalization, shadow-field mutation
- `apps/api/services/job_service.py` — create/list/filter/get/progress/cancel contract
- `apps/api/routers/jobs_v2.py` — public serialization/filtering boundary
- `apps/api/routers/collection_v2.py` + `apps/api/services/kra_collection_module.py` — async collection submission semantics
- `apps/api/tests/integration/test_jobs_v2_router_additional.py`, `apps/api/tests/unit/test_job_dispatch.py`, `apps/api/tests/unit/test_job_service.py`, `apps/api/tests/unit/test_async_tasks.py` — regression coverage entry points

</code_context>

<specifics>
## Specific Ideas

- 외부 job vocabulary는 implementation detail이 아니라 제품/API 용어를 유지해야 한다.
- 외부 lifecycle은 `processing` 중심으로 축소해 클라이언트 상태 해석을 단순하게 유지한다.
- `/api/v2/collection/async`는 외부에서 `batch` job 1개로 보는 현재 semantics를 유지한다.
- 이번 phase에서 compatibility를 길게 끌지 말고 canonical-only read로 cutover하되, planner는 그 cutover가 외부 vocabulary 선택과 충돌하지 않도록 schema/read path 전략을 명확히 제시해야 한다.

</specifics>

<deferred>
## Deferred Ideas

- durable queue, orphaned job recovery, explicit worker boundary — Phase 4 이후 execution platform work
- parent/child job graph 또는 race별 child job public exposure — 별도 capability, current phase scope 아님
- collection workflow 재구성 / deeper race processing module — Phase 5 성격으로 유지

### Reviewed Todos (not folded)
- `.planning/todos/pending/2026-04-05-deepen-race-processing-workflow.md` — collection/race workflow 응집도 문제는 중요하지만 job vocabulary 통일보다 더 큰 orchestration refactor이므로 이번 phase에 fold하지 않는다. 후속 phase에서 workflow boundary work와 함께 다룬다.

</deferred>

---

*Phase: 02-job-vocabulary*
*Context gathered: 2026-04-05*

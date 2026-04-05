# Roadmap: KRA Analysis

## Overview

이 로드맵은 이미 운영 중인 `apps/api` 중심 KRA 수집 플랫폼을 새 제품으로 확장하지 않고, 현재 활성 런타임 계약을 하나로 정리하는 순서다. 실행은 degraded health와 auth/logging wiring 안정화에서 시작해 jobs vocabulary와 runner 경계를 고정하고, unified migration bootstrap과 collection 서비스 분리를 거친 뒤 문서를 최종 source of truth로 맞춘다.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Runtime Guardrails** - health, logging, auth wiring을 현재 FastAPI 런타임 계약으로 고정한다.
- [ ] **Phase 2: Job Vocabulary** - async job 생성과 조회 응답이 하나의 작업 vocabulary를 사용하게 만든다.
- [ ] **Phase 3: Unified Bootstrap** - fresh DB bootstrap과 startup migration 검증을 unified chain 기준으로 고정한다.
- [ ] **Phase 4: Runner Boundary** - in-process job 실행 경계를 명시하고 handler 변경 비용을 줄인다.
- [ ] **Phase 5: Collection Seams** - collection 책임을 더 작은 경계로 분리하면서 기존 API 계약을 유지한다.
- [ ] **Phase 6: Contract Truth Docs** - schema, data lifecycle, 운영 명령 문서를 현재 코드 기준으로 일치시킨다.

## Phase Details

### Phase 1: Runtime Guardrails
**Goal**: Operator와 contributor가 degraded health, request logging, auth wiring을 하나의 런타임 계약으로 신뢰할 수 있다.
**Depends on**: Nothing (first phase)
**Requirements**: HEALTH-01, HEALTH-02, HEALTH-03
**Success Criteria** (what must be TRUE):
  1. Operator can call `/health/detailed` while Redis is unavailable and still receive HTTP 200 with an explicit degraded Redis status.
  2. Operator can inspect runtime logs and tests and see one canonical request logging path that redacts sensitive fields consistently.
  3. Contributor can trace one auth contract across dependency, policy, and accounting code without type mismatches.
**Plans**: TBD

### Phase 2: Job Vocabulary
**Goal**: Client가 job 생성, 상태 조회, 취소 응답에서 같은 작업 타입과 상태 vocabulary를 본다.
**Depends on**: Phase 1
**Requirements**: JOBS-01, JOBS-02
**Success Criteria** (what must be TRUE):
  1. Client can submit async collection jobs using one canonical job type set accepted by request DTOs and dispatch logic.
  2. Client can retrieve job status and cancellation responses that use the same canonical vocabulary shown at job creation.
  3. Contributor can inspect a submitted job in the database and API responses without translating between parallel alias names.
**Plans**: TBD

### Phase 3: Unified Bootstrap
**Goal**: Operator가 unified migration chain만으로 새 데이터베이스를 준비하고, 앱이 그 상태를 startup에서 검증한다.
**Depends on**: Phase 1
**Requirements**: SCHEMA-01, SCHEMA-02
**Success Criteria** (what must be TRUE):
  1. Operator can bootstrap a fresh database from the unified migration chain without relying on `create_all()` in the production path.
  2. App startup rejects missing or unexpected migration state against one canonical manifest in non-test environments.
  3. Operator can prove empty-database bootstrap with a documented migration-first verification path.
**Plans**: TBD

### Phase 4: Runner Boundary
**Goal**: Contributor가 async job handling을 하나의 실행 경계에서 바꾸되 기존 jobs API 동작은 유지할 수 있다.
**Depends on**: Phase 2, Phase 3
**Requirements**: JOBS-03
**Success Criteria** (what must be TRUE):
  1. Contributor can add or update job handling from one canonical dispatch boundary without maintaining parallel alias maps across router, DTO, ORM, and service layers.
  2. Client can keep using the existing `/api/v2/jobs/*` endpoints while runner internals are isolated behind the documented boundary.
  3. Operator can read the active execution contract and understand that current async work is in-process with explicit operational constraints.
**Plans**: TBD

### Phase 5: Collection Seams
**Goal**: Collection 도메인 책임이 더 작은 경계로 분리되면서 existing collection API behavior stays stable.
**Depends on**: Phase 4
**Requirements**: COLL-01, COLL-02
**Success Criteria** (what must be TRUE):
  1. Client can keep using existing collection endpoints without response regressions during prerace and result collection flows.
  2. Contributor can locate collection orchestration, enrichment, persistence, and external KRA transport responsibilities in separate modules or clearly named boundaries.
  3. Regression coverage demonstrates preserved collection API behavior while internal seams are clearer.
**Plans**: TBD

### Phase 6: Contract Truth Docs
**Goal**: Contributor와 operator가 active runtime, schema baseline, data lifecycle, quality commands를 하나의 truthful 문서 집합에서 이해할 수 있다.
**Depends on**: Phase 5
**Requirements**: SCHEMA-03, COLL-03, DOCS-01, DOCS-02
**Success Criteria** (what must be TRUE):
  1. Contributor can onboard from root and API docs without references to deleted apps, stale Celery assumptions, or inactive runtime paths.
  2. Operator can identify the authoritative unified schema baseline and migration flow from code and docs without consulting legacy branches.
  3. Operator can read one maintained doc set that explains prerace, result, and enriched data lifecycle against the current endpoints and storage model.
  4. Contributor can run one documented local and CI quality command set that matches checked-in scripts and workspace tasks.
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Runtime Guardrails | 0/TBD | Not started | - |
| 2. Job Vocabulary | 0/TBD | Not started | - |
| 3. Unified Bootstrap | 0/TBD | Not started | - |
| 4. Runner Boundary | 0/TBD | Not started | - |
| 5. Collection Seams | 0/TBD | Not started | - |
| 6. Contract Truth Docs | 0/TBD | Not started | - |

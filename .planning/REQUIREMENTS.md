# Requirements: KRA Analysis

**Defined:** 2026-04-05
**Core Value:** KRA 경주 데이터를 수집, 저장, 조회, 재실험하는 핵심 계약이 런타임, 스키마, 문서에서 모두 같은 사실을 말해야 한다.

## v1 Requirements

### Runtime Health

- [ ] **HEALTH-01**: Operator can call `/health/detailed` with Redis unavailable and still receive HTTP 200 with an explicit degraded component status.
- [ ] **HEALTH-02**: Operator can rely on one canonical request logging path that redacts sensitive request data consistently in runtime and tests.
- [ ] **HEALTH-03**: Contributor can use one consistent authentication and authorization contract without type mismatches across dependency, policy, and accounting paths.

### Job Contract

- [ ] **JOBS-01**: Client can submit async collection jobs using one canonical job type vocabulary accepted by request DTOs, persisted rows, and dispatch logic.
- [ ] **JOBS-02**: Client can retrieve job status and cancellation responses that use the same canonical vocabulary as job creation.
- [ ] **JOBS-03**: Contributor can add or update job handling without maintaining parallel alias maps across router, DTO, ORM, and service layers.

### Schema Bootstrap

- [ ] **SCHEMA-01**: Operator can bootstrap a fresh database from the unified migration chain without relying on `create_all()` in the production path.
- [ ] **SCHEMA-02**: App startup rejects missing or unexpected migration state against one canonical manifest in non-test environments.
- [ ] **SCHEMA-03**: Contributor can identify the authoritative schema baseline and migration flow from code and docs without consulting legacy branches.

### Collection Boundaries

- [ ] **COLL-01**: Client can keep using existing collection endpoints without response regressions while collection responsibilities are split into clearer seams.
- [ ] **COLL-02**: Contributor can locate collection orchestration, enrichment, persistence, and external KRA transport responsibilities in separate modules or clearly named boundaries.
- [ ] **COLL-03**: Operator can understand the meaning and lifecycle of prerace, result, and enriched data from one maintained doc set.

### Docs and Operations

- [ ] **DOCS-01**: Contributor can onboard from root/API documentation without references to deleted apps, stale Celery assumptions, or inactive runtime paths.
- [ ] **DOCS-02**: Contributor can follow one documented local and CI quality command set that matches the checked-in scripts and package tasks.

## v2 Requirements

### Execution Platform

- **EXEC-01**: Operator can move async collection jobs to a durable external queue without redesigning the API surface.
- **EXEC-02**: Operator can reconcile or replay orphaned jobs after process restarts.

### Security Hardening

- **SECU-01**: Operator can store API keys as hashed credentials with stable public identifiers instead of raw values in ownership/audit fields.
- **SECU-02**: Operator can enforce explicit production-safe auth and rate-limit defaults without hidden development fallbacks.

### Product Expansion

- **PROD-01**: User can access a clearer prediction-serving or experimentation surface beyond the current script-oriented tooling.
- **PROD-02**: Contributor can add new prediction or evaluation capabilities without coupling them tightly to the runtime API package.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Immediate durable queue rollout | Current milestone first needs a stable runner boundary and truthful operating contract |
| New frontend or dashboard surface | Current roadmap is backend and platform stabilization focused |
| Large prediction-model feature expansion | Data correctness, API contract unification, and schema reliability come first |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| HEALTH-01 | Phase 1 | Pending |
| HEALTH-02 | Phase 1 | Pending |
| HEALTH-03 | Phase 1 | Pending |
| JOBS-01 | Phase 2 | Pending |
| JOBS-02 | Phase 2 | Pending |
| SCHEMA-01 | Phase 3 | Pending |
| SCHEMA-02 | Phase 3 | Pending |
| JOBS-03 | Phase 4 | Pending |
| COLL-01 | Phase 5 | Pending |
| COLL-02 | Phase 5 | Pending |
| SCHEMA-03 | Phase 6 | Pending |
| COLL-03 | Phase 6 | Pending |
| DOCS-01 | Phase 6 | Pending |
| DOCS-02 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 14 total
- Mapped to phases: 14
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-05*
*Last updated: 2026-04-05 after roadmap initialization*

# Phase 2: Job Vocabulary - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-05
**Phase:** 02-job-vocabulary
**Areas discussed:** Canonical Job Type, Canonical Lifecycle Status, Async Collection Job Semantics, Legacy Compatibility Policy, Todo Fold Decision

---

## Canonical Job Type

| Option | Description | Selected |
|--------|-------------|----------|
| 제품/API 중심 vocabulary 유지 | 외부 canonical type은 `collection`, `batch`, `enrichment` 같은 도메인 용어로 고정하고 dispatch 용어는 내부 전용으로 둔다 | ✓ |
| 실행/dispatch 중심 vocabulary로 승격 | 외부도 `collect_race`, `batch_collect`, `full_pipeline` 같은 실행 단위 이름을 그대로 사용한다 | |
| 혼합 vocabulary 유지 | 외부와 내부를 계속 다르게 두고 alias/정규화로 봉합한다 | |

**User's choice:** 제품/API 중심 vocabulary 유지
**Notes:** external jobs API와 DB 관찰 경계는 제품 용어를 유지하고, dispatch vocabulary는 내부 구현 detail로만 남긴다.

---

## Canonical Lifecycle Status

| Option | Description | Selected |
|--------|-------------|----------|
| 외부 상태를 축소해서 canonical화 | 외부 lifecycle은 `pending`, `queued`, `processing`, `completed`, `failed`, `cancelled`로 고정하고 `running`/`retrying`은 내부 alias로만 둔다 | ✓ |
| 외부 상태를 세분화해서 유지 | `running`, `retrying`도 외부 1급 상태로 남긴다 | |
| 혼합 상태 유지 | 일부 경로만 정규화하고 나머지는 legacy를 유지한다 | |

**User's choice:** 외부 상태를 축소해서 canonical화
**Notes:** client-facing status는 `processing` 기준으로 단순화하고 runner detail은 노출하지 않는다.

---

## Async Collection Job Semantics

| Option | Description | Selected |
|--------|-------------|----------|
| 요청 단위 `batch` job 유지 | `/collection/async` 한 번 호출하면 외부 canonical type은 `batch` job 1개다 | ✓ |
| 외부에서도 `collection` job으로 통일 | 여러 race 요청도 외부에서는 모두 `collection`으로 보이게 한다 | |
| 부모/자식 job 모델로 드러냄 | 상위 `batch`와 하위 race별 `collection` job을 모두 public API에 노출한다 | |

**User's choice:** 요청 단위 `batch` job 유지
**Notes:** race별 실행은 내부 detail로만 남기고, public API는 request-level receipt/job model을 유지한다.

---

## Legacy Compatibility Policy

| Option | Description | Selected |
|--------|-------------|----------|
| canonical read 우선 + legacy fallback 유지 | canonical을 기본으로 삼되 old row를 위해 fallback read를 유지한다 | |
| 즉시 canonical-only cutover | 이번 phase에서 legacy read fallback을 제거하고 canonical-only read로 간다 | ✓ |
| dual-read/dual-write 장기 유지 | compatibility 구조를 계속 운영 계약으로 남긴다 | |

**User's choice:** 즉시 canonical-only cutover
**Notes:** 다만 canonical-only의 canonical은 제품/API vocabulary를 따라야 한다. planner는 shadow-field 상태를 그대로 승격하는 방식이 아니라, external product vocabulary와 충돌하지 않는 cutover/backfill/schema 전략을 제안해야 한다.

---

## Todo Fold Decision

| Option | Description | Selected |
|--------|-------------|----------|
| 이번 phase에 fold하지 않음 | `Deepen race processing workflow`는 deferred로 남긴다 | ✓ |
| 이번 phase에 일부 fold | vocabulary 정리에 필요한 seam 작업을 이번 phase scope에 같이 넣는다 | |

**User's choice:** 이번 phase에 fold하지 않음
**Notes:** collection/race workflow deepening은 Phase 5 성격으로 보고 이번 phase에서는 vocabulary 통일에 집중한다.

---

## the agent's Discretion

- canonical-only cutover를 schema migration, backfill, field repurposing 중 어떤 조합으로 구현할지는 research/planning 단계에서 결정한다.
- existing auth, ownership, pagination contract은 Phase 1 결정을 그대로 유지한다.

## Deferred Ideas

- deeper race processing workflow / collection orchestration consolidation
- parent-child public job model
- durable queue or worker-backed execution model

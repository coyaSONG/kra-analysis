# KRA Analysis

## What This Is

`KRA Analysis`는 한국마사회(KRA) 경주 데이터를 수집해 재사용 가능한 저장 구조로 정리하고, 그 데이터를 기반으로 예측 평가와 프롬프트 개선 실험을 반복하는 브라운필드 프로젝트다. 현재 운영 코어는 `apps/api`의 FastAPI 서버이고, 평가 및 실험 자동화는 `packages/scripts`에 분리되어 있다.

## Core Value

KRA 경주 데이터를 수집, 저장, 조회, 재실험하는 핵심 계약이 런타임, 스키마, 문서에서 모두 같은 사실을 말해야 한다.

## Requirements

### Validated

- ✓ KRA 경주 전 데이터를 `POST /api/v2/collection/`로 수집하고 DB에 저장할 수 있다 — existing
- ✓ 비동기 수집 작업을 생성하고 `GET /api/v2/jobs/*`에서 조회/취소할 수 있다 — existing
- ✓ `POST /api/v2/collection/result`로 경주 결과와 배당 데이터를 별도 수집할 수 있다 — existing
- ✓ API key 보호 경로와 `/health`, `/health/detailed`, `/metrics` 운영 엔드포인트가 존재한다 — existing
- ✓ `packages/scripts`에서 평가, 프롬프트 개선, 실험 보조 워크플로를 실행할 수 있다 — existing
- ✓ 작업 타입과 작업 상태 vocabulary가 DB, DTO, 서비스, 라우터, 문서에서 하나로 통일된다 — validated in Phase 2

### Active

- [ ] Redis degrade, health, logging, auth wiring이 하나의 일관된 런타임 계약으로 동작한다
- [ ] 새 데이터베이스를 unified migration chain만으로 bootstrap할 수 있고 canonical schema source of truth가 명확해진다
- [ ] collection 도메인 책임이 더 작은 경계로 분리되면서 기존 API 동작 계약은 유지된다
- [ ] README, API 가이드, 운영 문서가 실제 활성 구조와 명령만 설명한다

### Out of Scope

- 외부 durable queue를 즉시 도입하는 작업 — 우선 runner 경계와 운영 제약을 명확히 한 뒤 다음 마일스톤에서 다룬다
- 새로운 사용자용 UI 또는 별도 앱 표면 추가 — 현재 초점은 백엔드 계약 안정화와 데이터 파이프라인 신뢰성이다
- 예측 모델 자체의 대규모 기능 확장 — 현재 범위는 데이터/플랫폼 정합성과 실험 기반 유지보수성 확보다

## Context

- 저장소는 `pnpm` 워크스페이스 기반 모노레포지만 현재 활성 런타임은 `apps/api/main_v2.py` 한 곳에 집중되어 있다.
- `apps/api`는 FastAPI, SQLAlchemy async ORM, PostgreSQL, Redis, in-process `asyncio` background task 조합으로 동작한다.
- `packages/scripts`는 운영 API와 별개로 평가, 프롬프트 개선, 실험 자동화를 담당한다.
- `.planning/codebase/*.md` 기준으로 현재 주요 리스크는 in-process 작업 실행기, 분열된 job vocabulary, legacy/unified migration 공존, 비대한 `CollectionService`, 드리프트된 문서다.
- `docs/plans/2026-03-19-architecture-remediation-execplan.md`는 현재 액티브 개선 방향을 가장 구체적으로 설명하는 canonical 실행 문서다.
- 이 프로젝트는 "새 제품을 만든다"기보다 "이미 동작 중인 데이터 수집/실험 플랫폼을 단일 계약 시스템으로 정리한다"는 성격이 강하다.

## Current State

- Phase 2 complete — jobs create/read/cancel and async collection follow-up now share one canonical public vocabulary.
- Next focus is Phase 3, which locks unified migration bootstrap and startup schema verification to the active migration manifest.

## Constraints

- **Tech stack**: Python 3.13+, FastAPI, SQLAlchemy async ORM, PostgreSQL, Redis, `uv`, `pnpm` — 현재 활성 런타임과 CI 체인을 유지해야 한다
- **Brownfield**: 이미 운영 중인 API와 실험 스크립트가 존재 — 기존 엔드포인트와 저장 구조를 무리하게 끊을 수 없다
- **API compatibility**: `collection`, `jobs`, `health`, `metrics` 경로는 유지되어야 한다 — 기존 호출자와 테스트 자산을 깨지 않기 위해서다
- **Operational safety**: Redis 장애, migration drift, background job 유실 가능성을 고려해야 한다 — 플랫폼 안정화가 현재 최우선 과제이기 때문이다
- **Documentation truthfulness**: 문서가 실제 코드와 어긋나면 안 된다 — 신규 기여자가 잘못된 구조를 학습하는 비용이 이미 발생하고 있기 때문이다
- **Version control**: 계획 문서는 git에 추적한다 — 현재 저장소 관례와 세션 복원성을 유지하기 위해서다

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 현재 초기화 범위는 "플랫폼 안정화 및 계약 통일"로 둔다 | 기존 코드와 문서가 이미 이 방향으로 수렴하고 있고, 현재 리스크가 기능 부족보다 계약 분열에서 크기 때문이다 | — Pending |
| 브라운필드 초기화로 취급하고 기존 동작을 Validated requirements로 기록한다 | 이미 제공 중인 수집/작업/결과/실험 기능을 기준선으로 삼아야 이후 개선 범위를 정확히 나눌 수 있기 때문이다 | — Pending |
| active schema baseline은 unified migration 계열을 기준으로 정리한다 | 현재 ORM과 운영 경로가 legacy baseline보다 unified 쪽에 더 가깝기 때문이다 | — Pending |
| planning 문서는 git에 커밋한다 | 이 저장소는 이미 `.planning` 산출물을 추적하고 있고, GSD 워크플로 복원성에도 유리하기 때문이다 | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check -> still the right priority?
3. Audit Out of Scope -> reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-05 after Phase 2 completion*

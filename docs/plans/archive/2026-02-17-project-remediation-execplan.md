# Project Reliability Remediation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** API/Collector/CI에서 확인된 계약 불일치, 캐시 무결성 문제, 테스트/문서 드리프트를 제거해 "응답이 실제 구현 상태를 정직하게 반영하는" 저장소 상태를 만든다.

**Architecture:** FastAPI(`apps/api`)와 Express+TypeScript(`apps/collector`)를 각각 서비스 경계 중심으로 정리한다. API는 비동기 작업 계약과 조회 계약을 일치시키고, Collector는 날짜별 조회 및 캐시 삭제 의미를 명확히 만든다. CI는 lockfile 고정과 불필요 빌드 의존 제거로 재현성을 복구한다.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy async, TypeScript(ESM), Express, Jest, pnpm workspaces, Turborepo, GitHub Actions.

---

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

`PLANS.md` is checked into this repository at `.agent/PLANS.md`. This document must be maintained in accordance with `.agent/PLANS.md`.

## Purpose / Big Picture

현재 저장소에는 "성공처럼 보이는 응답"과 "실제 처리 상태"가 어긋나는 경로가 존재한다. 대표적으로 `apps/api/routers/collection_v2.py:84`는 작업을 생성하지 않으면서 `job_id`를 반환하고, `apps/collector/src/controllers/race.controller.ts:68`은 실제 조회 없이 빈 배열을 정상 응답으로 돌려준다. 이런 경로는 기능이 완성되지 않았는데도 운영 관점에서는 성공처럼 보이기 때문에, 장애 탐지와 회귀 검증을 어렵게 만든다.

이 계획이 완료되면 다음이 가능해야 한다.

1. 비동기 수집 API를 호출하면 실제 추적 가능한 작업이 생성되고, `GET /api/v2/jobs/{job_id}`에서 같은 ID를 조회할 수 있다.
2. 날짜별 레이스 조회 API가 더미 빈 배열이 아니라 실제 수집 경로를 타거나, 실패 시 명확한 오류를 반환한다.
3. 캐시 clear가 타입 단위로 안전하게 동작해, 다른 타입 캐시가 의도치 않게 삭제되지 않는다.
4. CI가 lockfile 기준으로 재현 가능하게 실행되고, 개발/테스트 사이클에서 불필요한 전체 빌드를 강제하지 않는다.

## Progress

- [x] (2026-02-17 15:24Z) 감사 결과를 근거 파일/라인까지 재확인했고 본 ExecPlan 초안을 작성했다.
- [ ] Milestone 1 완료: API 비동기 작업 계약(생성/조회) 및 잡 목록 카운트 일관성 복구.
- [ ] Milestone 2 완료: Collector 날짜 조회의 더미 응답 제거 및 서비스 경로 연동.
- [ ] Milestone 3 완료: 파일 캐시 clear를 패턴 안전 방식으로 전환하고 회귀 테스트 추가.
- [ ] Milestone 4 완료: Collector 네트워크 타임아웃/force refresh 동작을 환경 독립적으로 안정화.
- [ ] Milestone 5 완료: CI 설치/터보 의존성/문서/테스트 중복 정리를 반영하고 전체 회귀를 통과.

## Surprises & Discoveries

- Observation: FastAPI 비동기 수집 엔드포인트는 `job_id`를 반환하지만 실제 job persistence가 없다.
  Evidence: `apps/api/routers/collection_v2.py:97-107`.

- Observation: `jobs` 목록 API는 라우터와 서비스가 각각 필터/카운트 책임을 나눠 가져 드리프트 위험이 있다.
  Evidence: `apps/api/routers/jobs_v2.py:77-88`, `apps/api/services/job_service.py:271-313`.

- Observation: Collector 파일 캐시 clear는 패턴 인자를 받지만 구현은 전체 JSON 삭제에 가깝다.
  Evidence: `apps/collector/src/services/cache.service.ts:474-489`.

- Observation: Collector 날짜 조회는 "실제 구현 TODO" 주석과 함께 빈 배열 성공 응답을 반환한다.
  Evidence: `apps/collector/src/controllers/race.controller.ts:65-77`.

- Observation: CI의 Node 설치 단계가 lockfile 고정을 해제해 실행 시점별 결과가 달라질 수 있다.
  Evidence: `.github/workflows/ci.yml:119`, `.github/workflows/ci.yml:155`.

## Decision Log

- Decision: `/api/v2/collection/async`는 "실행 가능한 작업 생성"이 끝날 때까지 임시 성공 응답을 유지하지 않고, 실제 job 생성-조회가 검증된 경로로만 운영한다.
  Rationale: 계약 정직성을 우선해 가짜 성공을 제거한다.
  Date/Author: 2026-02-17 / Codex.

- Decision: 잡 목록 total 계산 책임을 서비스 계층으로 모아 라우터의 중복 SQL을 제거한다.
  Rationale: 필터 변경 시 한 곳만 수정하도록 만들어 회귀 확률을 낮춘다.
  Date/Author: 2026-02-17 / Codex.

- Decision: 파일 캐시는 "원본 키 메타데이터"를 저장해 clear의 패턴 매칭을 보수적으로 구현한다.
  Rationale: 해시 기반 파일명만으로는 prefix 삭제를 정확히 수행할 수 없다.
  Date/Author: 2026-02-17 / Codex.

- Decision: CI는 `--frozen-lockfile`을 강제하고, `turbo`의 dev/test 계열 태스크에서 불필요한 `^build` 의존을 제거한다.
  Rationale: 재현성과 피드백 속도를 동시에 확보한다.
  Date/Author: 2026-02-17 / Codex.

## Outcomes & Retrospective

초기 상태 기록 (작성 시점):

- API/Collector 핵심 경로에 placeholder 성공 응답이 남아 있고, 운영 상태를 오도할 여지가 존재한다.
- 캐시 clear semantics가 API 문서 의미와 구현 의미가 다르다.
- CI 설치 전략이 lockfile 비고정이어서 로컬/CI 결과 차이가 발생할 수 있다.

완료 시점에는 본 섹션에 "실제 동작 변화", "남은 리스크", "추가 후속 작업"을 업데이트한다.

## Context and Orientation

이 저장소는 pnpm 모노레포이며, 이번 작업의 핵심 맥락은 세 영역이다.

첫째, `apps/api`는 FastAPI v2 서버이며 `apps/api/main_v2.py`에서 `collection_v2`와 `jobs_v2` 라우터를 노출한다. 비동기 작업 관리는 `apps/api/services/job_service.py`가 담당하고, 백그라운드 실행은 `apps/api/infrastructure/background_tasks.py`를 통해 처리한다.

둘째, `apps/collector`는 Express 기반 API다. `apps/collector/src/controllers/race.controller.ts`가 날짜별 조회/상세 조회를 담당하고, `apps/collector/src/services/cache.service.ts`와 `apps/collector/src/services/enrichment.service.ts`가 캐시 및 보강 흐름을 담당한다.

셋째, 실행 파이프라인은 `.github/workflows/ci.yml`과 `turbo.json`에 정의된다. lockfile 사용 방식과 task dependency 설정이 개발 경험과 CI 신뢰성을 직접 좌우한다.

이 문서에서 사용하는 용어는 다음 의미로 고정한다.

- 계약 정직성(contract integrity): 엔드포인트의 HTTP 상태코드와 본문이 실제 구현 상태를 거짓 없이 반영하는 성질.
- 서비스 경계(service boundary): 필터/카운트/조회 규칙 같은 비즈니스 규칙이 라우터가 아니라 서비스에 한 번만 정의된 상태.
- 패턴 안전 캐시 삭제(pattern-safe clear): `enriched_race:*` 삭제 시 다른 prefix(`race_result:*`) 항목을 삭제하지 않는 동작.

## Milestones

### Milestone 1: API 비동기 작업 계약과 목록 조회 일관성 복구

이 마일스톤이 끝나면 `/api/v2/collection/async` 호출 결과로 생성된 `job_id`가 실제 DB에 존재하고, 같은 ID를 `/api/v2/jobs/{job_id}`로 조회할 수 있어야 한다. 또한 `/api/v2/jobs/`의 `total`은 목록 조회와 동일 필터 기준으로 계산되어야 한다.

핵심 수정 파일은 `apps/api/routers/collection_v2.py`, `apps/api/routers/jobs_v2.py`, `apps/api/services/job_service.py`, `apps/api/tests/integration/test_api_endpoints.py`, `apps/api/tests/unit/test_job_service.py`다.

검증은 `apps/api` 작업 디렉터리에서 `uv run pytest -q`와 대상 테스트 재실행으로 수행한다.

### Milestone 2: Collector 날짜 조회 API의 더미 성공 응답 제거

이 마일스톤이 끝나면 `GET /api/v1/races/:date`가 단순 빈 배열을 반환하지 않고 실제 수집 경로(`collectDay`)를 통해 데이터 또는 명확한 오류를 반환해야 한다. 캐시 히트 시만 캐시 응답을 반환하고, 미스 시 수집 경로가 호출되어야 한다.

핵심 수정 파일은 `apps/collector/src/controllers/race.controller.ts`, `apps/collector/tests/controllers/race.controller.test.ts`, `apps/collector/tests/integration/api.test.ts`다.

검증은 `pnpm -F @apps/collector test -- tests/controllers/race.controller.test.ts` 후 전체 collector 테스트로 수행한다.

### Milestone 3: 파일 캐시 clear의 패턴 안전성 확보

이 마일스톤이 끝나면 `cache.clear('enriched_race')` 실행 시 `enriched_race` prefix에 속한 파일만 삭제되고 다른 타입 캐시는 남아 있어야 한다.

핵심 수정 파일은 `apps/collector/src/services/cache.service.ts`, `apps/collector/tests/services/cache.service.test.ts`다.

검증은 기존 clear 테스트를 "타입 간 격리"를 검증하는 형태로 확장해 수행한다.

### Milestone 4: Collector 네트워크/캐시 갱신 동작 안정화

이 마일스톤이 끝나면 `AbortSignal.timeout()` 미지원 환경에서도 타임아웃이 동작해야 하고, `forceRefresh` 경로는 캐시를 명시적으로 무효화한 뒤 재조회해야 한다.

핵심 수정 파일은 `apps/collector/src/services/kraApiService.ts`, `apps/collector/src/services/enrichment.service.ts`, `apps/collector/tests/services/kra-api.service.test.ts`이며 필요하면 `apps/collector/tests/services/enrichment.service.test.ts`를 신설한다.

검증은 타임아웃/forceRefresh 전용 테스트 + collector 전체 테스트로 수행한다.

### Milestone 5: CI 재현성, 개발 피드백 루프, 문서/테스트 드리프트 정리

이 마일스톤이 끝나면 CI 설치는 lockfile 고정으로 동작하고, `turbo` dev/test는 불필요한 선행 build 없이 시작한다. 문서와 테스트 자산은 현재 코드 구조와 일치하도록 정리한다.

핵심 수정 파일은 `.github/workflows/ci.yml`, `turbo.json`, `docs/unified-collection-api-design.md`, `apps/collector/TEST_GUIDE.md`, `apps/api/tests/conftest.py`, `apps/api/tests/unit/test_logging_middleware.py`, `apps/api/tests/unit/test_middleware_logging.py`, `apps/api/test_api.py`, `apps/api/tests/test_api.py`다.

검증은 워크스페이스 테스트와 lint/typecheck를 포함한 회귀 실행으로 수행한다.

## Plan of Work

작업은 TDD 순서로 진행한다. 각 마일스톤마다 먼저 실패하는 테스트를 만들고, 최소 구현으로 통과시키고, 관련 스코프 전체 테스트를 다시 실행한 뒤 커밋한다. 한 번에 여러 축을 건드리지 않고, 마일스톤 단위로 경계를 고정해 회귀 원인을 즉시 좁힐 수 있게 한다.

Milestone 1에서는 API 계약 복구를 먼저 처리한다. `collection_v2`는 실제 Job 생성과 시작까지 연결하고, `jobs_v2`는 total 계산을 서비스로 위임한다. 이 단계에서 라우터 내 직접 SQL 필터 중복을 제거한다.

Milestone 2와 3은 Collector 기능 정확성을 다룬다. 날짜 조회가 더미 성공 응답을 주지 않도록 경로를 실데이터 수집 경로로 통일하고, 파일 캐시 clear는 메타데이터 기반 prefix 매칭으로 교체한다.

Milestone 4는 런타임 회복탄력성이다. 네트워크 타임아웃 구현을 환경 독립적으로 바꾸고, force refresh에서 stale 캐시를 명시적으로 제거한 뒤 다시 채우도록 한다.

Milestone 5는 운영 유지보수성을 마무리한다. CI 재현성, turbo 태스크 의존, 문서-코드 불일치, 테스트 중복/미사용 fixture를 정리한다.

## Concrete Steps

1. API 계약 복구용 실패 테스트를 먼저 추가한다.

   Working directory: `apps/api`.

   Run:
     uv run pytest -q tests/integration/test_api_endpoints.py -k async_collect_races

   Expected before fix:
     - 테스트가 `job_id` 존재만 확인하고 실제 `GET /api/v2/jobs/{job_id}` 조회를 검증하지 않음.

   Edit:
     - `apps/api/tests/integration/test_api_endpoints.py`에서 async collect 후 `GET /api/v2/jobs/{job_id}`가 200인지 검증하는 assertion 추가.

2. `collection_v2`를 실제 Job 생성 흐름으로 연결한다.

   Edit:
     - `apps/api/routers/collection_v2.py` `collect_race_data_async`에서 `JobService.create_job()`와 `start_job()`를 호출한다.
     - 파라미터는 `_dispatch_task`가 요구하는 키(`race_date`, `meet`, `race_numbers`)를 사용한다.
     - 오류 시 500 대신 의미 있는 오류 메시지를 포함해 raise한다.

3. 잡 목록 total 계산 책임을 서비스로 이동한다.

   Edit:
     - `apps/api/services/job_service.py`에 `list_jobs_with_total(...) -> tuple[list[Job], int]` 추가.
     - `apps/api/routers/jobs_v2.py`에서 `SAJob` 직접 조회/`func.count()` 중복 코드를 제거하고 새 서비스 메서드 사용.

   Run:
     uv run pytest -q tests/integration/test_api_endpoints.py -k "list_jobs or async_collect_races"
     uv run pytest -q tests/unit/test_job_service.py

4. Collector 날짜 조회 API를 실수집 경로로 연결한다.

   Edit:
     - `apps/collector/src/controllers/race.controller.ts`의 `getRacesByDate`에서 캐시 미스 시 `services.collectionService.collectDay(...)` 호출.
     - `meet` query가 있으면 단일 meet, 없으면 서비스 기본 동작으로 처리.
     - 기존 "simulate" 주석/빈 배열 기본 응답 제거.

   Run:
     pnpm -F @apps/collector test -- tests/controllers/race.controller.test.ts

5. 파일 캐시 clear를 패턴 안전 방식으로 수정한다.

   Edit:
     - `apps/collector/src/services/cache.service.ts`의 file entry 구조에 `key`(원본 캐시 키)를 포함해 저장.
     - `clearFromFile(pattern)`에서 entry의 `key`를 읽어 prefix가 일치하는 항목만 삭제.
     - 기존 "aggressive delete all" 주석과 TODO 제거.

   Test update:
     - `apps/collector/tests/services/cache.service.test.ts`에 "enriched_race clear 후 race_result는 남아야 함" 케이스 추가.

   Run:
     pnpm -F @apps/collector test -- tests/services/cache.service.test.ts

6. 타임아웃/forceRefresh 안정화 테스트를 먼저 작성하고 구현한다.

   Edit:
     - `apps/collector/src/services/kraApiService.ts`: `AbortSignal.timeout` 직접 의존 대신 `AbortController + setTimeout` 기반 helper로 교체.
     - `apps/collector/src/services/enrichment.service.ts`: `forceRefresh=true`일 때 해당 키 `cacheService.delete(...)` 후 `getOrSet` 또는 fetch 경로를 호출.

   Test:
     - `apps/collector/tests/services/kra-api.service.test.ts`에 timeout helper 경로 검증 추가.
     - 필요 시 `apps/collector/tests/services/enrichment.service.test.ts` 신설 후 forceRefresh 동작 검증.

   Run:
     pnpm -F @apps/collector test -- tests/services/kra-api.service.test.ts
     pnpm -F @apps/collector test

7. CI/터보/문서/테스트 드리프트 정리.

   Edit:
     - `.github/workflows/ci.yml`의 `pnpm install --no-frozen-lockfile`를 `pnpm install --frozen-lockfile`로 변경.
     - `turbo.json`의 `dev`, `test`, `test:ci`에서 `dependsOn: ["^build"]` 제거 또는 필요한 워크스페이스만 제한.
     - `docs/unified-collection-api-design.md`의 v1 샘플(`main.py`) 구간을 `main_v2.py` 기준으로 수정하거나 legacy로 명시.
     - `apps/collector/TEST_GUIDE.md`의 실제 테스트 트리(`controllers`, `services`) 반영.
     - `apps/api/tests/conftest.py`의 미사용 fixture(`sample_race_request`, `sample_job_data`) 제거 또는 재사용.
     - `apps/api/tests/unit/test_logging_middleware.py`와 `apps/api/tests/unit/test_middleware_logging.py`의 request-id 중복 검증을 단일 파일로 통합.
     - `apps/api/test_api.py`와 `apps/api/tests/test_api.py`의 중복 수동 스크립트를 하나로 정리.

   Run:
     (cd apps/api && uv run pytest -q)
     pnpm -F @apps/collector test
     pnpm turbo run lint typecheck
     pnpm test

8. 마무리 검증 및 문서 갱신.

   Run:
     git diff --stat
     git status --short

   Update:
     - 본 문서의 `Progress`, `Decision Log`, `Outcomes & Retrospective`를 실제 결과로 갱신.

## Validation and Acceptance

수용 기준은 내부 구조가 아니라 사용자 행동으로 검증한다.

1. API 비동기 작업 계약.
   - `POST /api/v2/collection/async`가 202를 반환하고 본문에 `job_id`가 포함된다.
   - 같은 `job_id`로 `GET /api/v2/jobs/{job_id}` 호출 시 200과 동일 ID가 반환된다.

2. 잡 목록 total 일관성.
   - 상태 필터로 조회한 `/api/v2/jobs/?status=completed`의 `total`이 같은 필터의 실제 레코드 수와 일치한다.

3. Collector 날짜 조회 실동작.
   - 캐시 미스 환경에서 `GET /api/v1/races/:date`가 더미 빈 배열 메시지가 아니라 실제 수집 경로 결과를 반환한다.

4. 캐시 clear 안전성.
   - `clear('enriched_race')` 실행 후 `enriched_race:*`는 삭제되고 `race_result:*`는 유지된다.

5. CI 재현성.
   - lockfile 변경 없이 CI 설치가 실패하지 않고, 로컬 `pnpm install --frozen-lockfile` 결과와 동일 트리로 테스트가 실행된다.

## Idempotence and Recovery

모든 변경은 재실행 가능해야 한다. 테스트 추가/수정은 여러 번 실행해도 상태를 오염시키지 않아야 하며, 파일 캐시 테스트는 고정된 테스트 디렉터리(`cache-test-jest`)를 사용하고 종료 시 정리한다.

마일스톤 중간 실패 시 복구 절차는 다음과 같다.

1. 마지막 성공 테스트 커맨드를 다시 실행해 실패 범위를 고정한다.
2. 해당 마일스톤 파일만 대상으로 `git diff <path>`를 확인한다.
3. 실패 원인 수정 후 같은 테스트를 재실행한다.
4. 마일스톤 스코프 테스트가 통과한 뒤에만 다음 마일스톤으로 진행한다.

데이터 마이그레이션이나 파괴적 DB 작업은 본 계획 범위에 포함하지 않는다.

## Artifacts and Notes

예상 HTTP 시나리오 (완료 후):

  POST /api/v2/collection/async
  Request body: {"date":"20240719","meet":1,"race_numbers":[1,2,3]}
  Response 202: {"job_id":"<uuid>","status":"accepted",...}

  GET /api/v2/jobs/<same-uuid>
  Response 200: {"job":{"job_id":"<same-uuid>","status":"queued"|"processing"|...}}

예상 캐시 시나리오 (완료 후):

  set('race_result', ...)
  set('enriched_race', ...)
  clear('enriched_race')
  exists('enriched_race', ...) == false
  exists('race_result', ...) == true

## Interfaces and Dependencies

구현 완료 시 아래 인터페이스를 만족해야 한다.

- `apps/api/services/job_service.py`
  - 새 메서드: `async def list_jobs_with_total(self, db: AsyncSession, user_id: str | None = None, job_type: str | None = None, status: str | None = None, limit: int = 20, offset: int = 0) -> tuple[list[Job], int]`.
  - `list_jobs`는 필요하면 wrapper로 유지하되 필터 로직은 한 군데만 유지한다.

- `apps/api/routers/jobs_v2.py`
  - 라우터 레벨 `SAJob` 직접 카운트 쿼리를 제거하고 `JobService` 메서드 호출만 사용한다.

- `apps/collector/src/services/cache.service.ts`
  - 파일 캐시 entry 타입은 원본 키(`key`)를 저장해야 한다.
  - `clearFromFile(pattern)`은 pattern prefix 매칭 파일만 삭제해야 한다.

- `apps/collector/src/services/kraApiService.ts`
  - 타임아웃 구현이 `AbortSignal.timeout` 존재 여부에 의존하지 않아야 한다.
  - helper는 timeout 종료 시 abort를 보장하고 timer cleanup을 보장해야 한다.

- `.github/workflows/ci.yml`
  - Node install 단계는 lockfile 고정 옵션을 사용해야 한다.

## Change Note

- 2026-02-17 / Codex: 신규 ExecPlan 파일 생성. 전수조사 결과(P1/P2)를 구현 가능한 마일스톤으로 재구성하고, 각 마일스톤별 파일/검증 커맨드/수용 기준을 명시했다.

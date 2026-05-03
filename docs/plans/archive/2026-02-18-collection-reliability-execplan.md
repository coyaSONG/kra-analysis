# Collection Reliability and Status Observability ExecPlan

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

`PLANS.md` is checked into this repository at `.agent/PLANS.md`. This document must be maintained in accordance with `.agent/PLANS.md`.

## Purpose / Big Picture

이 변경의 목표는 "수집이 얼마나 진행됐는지"를 시스템이 정직하게 보여주는 것이다. 완료 후에는 `GET /api/v2/collection/status`가 하드코딩 값이 아니라 실제 DB 상태를 반환하고, 운영자는 날짜/경마장 기준 수집 진행률을 숫자로 확인할 수 있다. 또한 로컬/운영에서 DB 연결 문제가 있을 때 즉시 원인을 확인할 수 있는 점검 경로를 제공한다.

## Progress

- [x] (2026-02-18 01:31 KST) 실행 워크트리(`.worktrees/collection-reliability-exec`)와 작업 브랜치(`feat/collection-reliability-exec`)를 생성했다.
- [x] (2026-02-18 01:33 KST) 현재 상태 API가 고정 응답(`total_races=15`, `collected=0`)인 점을 재확인했다.
- [x] (2026-02-18 01:35 KST) 통합 테스트를 추가해 RED를 확인했다 (`assert 15 == 2` 실패).
- [x] (2026-02-18 01:37 KST) `CollectionService.get_collection_status`를 구현하고 라우터 TODO 응답을 제거했다.
- [x] (2026-02-18 01:38 KST) 관련 테스트를 GREEN으로 확인했다.
- [x] (2026-02-18 01:41 KST) 진단 모듈(`services/collection_status_diagnostics.py`)과 CLI(`scripts/check_collection_status_db.py`)를 추가했다.
- [x] (2026-02-18 01:42 KST) 진단 모듈 테스트 RED/GREEN을 완료했다.
- [x] (2026-02-18 01:43 KST) 로컬에서 진단 스크립트를 실행해 DB 인증 실패 원인 메시지를 확인했다.
- [x] (2026-02-18 01:43 KST) Milestone 0 완료: DB 연결 정합성 점검 경로 추가 및 로컬 실행 확인.
- [x] (2026-02-18 01:38 KST) Milestone 1 완료: `/api/v2/collection/status`를 실제 DB 집계 기반으로 구현.
- [x] (2026-02-18 01:38 KST) Milestone 2 완료: 수집 상태 집계의 회귀 테스트(TDD red-green) 추가.
- [x] (2026-02-18 01:43 KST) `apps/api/README.md`, `apps/api/docs/QUICK_START.md`에 운영 진단 사용 예시를 반영했다.
- [x] (2026-02-18 01:45 KST) Milestone 3 완료: 문서/운영 사용 예시 업데이트 및 최종 검증.
- [x] (2026-02-18 01:45 KST) `apps/api` 전체 테스트(`uv run pytest -q`)를 실행해 회귀가 없음을 확인했다.

## Surprises & Discoveries

- Observation: 테스트 환경은 in-memory SQLite를 사용하므로 운영 DB 인증 실패와 분리되어 API 집계 로직을 안전하게 검증할 수 있다.
  Evidence: `apps/api/tests/conftest.py`의 `database_url="sqlite+aiosqlite:///:memory:"`.

- Observation: `pytest.ini`에 전역 `--cov` 옵션이 고정되어 있어 부분 테스트 실행 시 커버리지 미달로 실패한다.
  Evidence: `uv run pytest -q tests/integration/test_api_endpoints.py -k collection_status` 실행 시 `Coverage failure: total of 25 is less than fail-under=75`.

- Observation: 현재 워크트리의 `DATABASE_URL`은 로컬 기본값(`kra_user@localhost`)이라 즉시 인증 오류를 재현할 수 있었다.
  Evidence: `uv run python scripts/check_collection_status_db.py` 실행 시 `password authentication failed`.

## Decision Log

- Decision: 상태 집계 로직은 라우터가 아니라 `CollectionService`에 두고 라우터는 입출력만 담당한다.
  Rationale: 도메인 계산 규칙을 서비스 계층으로 모아 추후 재사용/테스트를 쉽게 만든다.
  Date/Author: 2026-02-18 / Codex.

- Decision: overall status는 `pending|running|completed`로 유지하되, 세부 상태(`collection_status`, `enrichment_status`)를 함께 반환한다.
  Rationale: 기존 클라이언트 호환성을 유지하면서 운영 진단 정보를 늘린다.
  Date/Author: 2026-02-18 / Codex.

- Decision: 부분 검증에서는 `--override-ini addopts=''`로 커버리지 강제 옵션을 잠시 해제해 기능 회귀를 확인한다.
  Rationale: 전체 커버리지 게이트는 전체 테스트에서 검증하고, 개발 중 red-green 검증은 대상 테스트 신호를 우선 본다.
  Date/Author: 2026-02-18 / Codex.

- Decision: DB 점검은 기존 `test_db_connection.py`를 대체하지 않고, 수집 운영 관점 진단(`jobs/races/collection status`) 전용 스크립트를 별도로 추가한다.
  Rationale: 연결 자체 점검과 수집 운영 점검의 목적이 달라 출력 포맷과 실행 인자가 분리된 편이 유지보수에 유리하다.
  Date/Author: 2026-02-18 / Codex.

## Outcomes & Retrospective

최종 결과(2026-02-18 01:45 KST):

- 상태 API가 더 이상 하드코딩 값을 반환하지 않고 DB 집계값을 반환한다.
- 수집 상태 집계의 회귀 테스트가 추가되어 동일 회귀를 자동 탐지할 수 있다.
- DB 연결/집계 진단 스크립트가 추가되어 운영자가 CLI로 `jobs/races` 상태를 즉시 점검할 수 있다.
- 문서에 진단 스크립트 사용 예시가 반영되어 온보딩 시 점검 절차가 명확해졌다.
- `apps/api` 전체 테스트 232 passed, 2 skipped, coverage 79.67%로 회귀 없이 기준(75%)을 만족했다.

## Context and Orientation

핵심 변경 경로는 `apps/api` 아래 세 곳이다. `apps/api/routers/collection_v2.py`는 `/api/v2/collection/status` 엔드포인트를 제공하지만 현재는 TODO 응답이다. `apps/api/services/collection_service.py`는 수집 도메인 로직을 담당하므로 상태 집계 계산 로직의 적절한 위치다. `apps/api/tests/integration/test_api_endpoints.py`는 API 계약을 검증하는 통합 테스트 파일로, 여기서 red-green 테스트를 작성한다.

여기서 "상태 집계"는 특정 `date`와 `meet`에 대해 `races` 테이블을 조회해 `total_races`, `collected_races`, `enriched_races`, `last_updated`를 계산하는 동작을 뜻한다. `overall status`는 집계 결과를 `pending`, `running`, `completed` 중 하나로 축약한 값이다.

## Plan of Work

먼저 통합 테스트를 추가해 현재 고정 응답이 실패하도록 만든다. 그 다음 `CollectionService`에 상태 집계 메서드를 추가하고 라우터에서 이를 호출하게 바꾼다. 마지막으로 DB 연결 점검용 스크립트 또는 명령 경로를 추가해 운영 시점 진단 가능성을 보강한다. 각 단계마다 테스트를 다시 실행해 회귀를 막는다.

## Concrete Steps

1. `apps/api/tests/integration/test_api_endpoints.py`에 "DB에 race 2건이 있으면 status 응답이 total=2를 반환"하는 테스트를 추가한다.
2. 새 테스트만 실행해 RED(실패)를 확인한다.
3. `apps/api/services/collection_service.py`에 상태 집계 메서드를 추가한다.
4. `apps/api/routers/collection_v2.py`에서 TODO 응답 대신 서비스 집계 결과를 반환한다.
5. 테스트를 다시 실행해 GREEN(성공)을 확인한다.
6. 관련 API 테스트 묶음을 추가 실행해 부작용이 없는지 확인한다.

## Validation and Acceptance

수용 기준은 다음과 같다.

- DB에 해당 날짜/경마장 race 레코드가 없으면 `total_races=0`, `status="pending"`을 반환한다.
- DB에 수집 완료 레코드가 존재하면 `collected_races`가 0보다 커지고 `status`가 `running` 또는 `completed`가 된다.
- 추가된 통합 테스트가 변경 전 실패하고 변경 후 통과한다.

검증 명령은 `apps/api` 작업 디렉터리에서 실행한다.

- `uv run pytest --override-ini addopts='' -q tests/integration/test_api_endpoints.py -k collection_status`
- `uv run pytest --override-ini addopts='' -q tests/unit/test_collection_router_more_errors.py`

## Idempotence and Recovery

테스트 데이터는 pytest fixture가 함수 단위로 생성/삭제하므로 반복 실행해도 누적 오염이 없다. 구현 도중 실패하면 변경 파일만 되돌리고 테스트를 다시 실행하면 동일 상태에서 재시도할 수 있다.

## Artifacts and Notes

RED 증거:

    tests/integration/test_api_endpoints.py::test_get_collection_status_counts_from_database
    E   assert 15 == 2

GREEN 증거:

    uv run pytest --override-ini addopts='' -q tests/integration/test_api_endpoints.py -k collection_status
    4 passed, 19 deselected

    uv run pytest --override-ini addopts='' -q tests/unit/test_collection_router_more_errors.py
    3 passed

진단 모듈 RED/GREEN 증거:

    uv run pytest --override-ini addopts='' -q tests/unit/test_collection_status_diagnostics.py
    E   ModuleNotFoundError: No module named 'services.collection_status_diagnostics'

    uv run pytest --override-ini addopts='' -q tests/unit/test_collection_status_diagnostics.py
    2 passed

로컬 점검 실행 증거:

    uv run python scripts/check_collection_status_db.py --date 20260214 --meet 1
    DB Connection Error
    password authentication failed

전체 회귀 검증 증거:

    uv run pytest -q
    232 passed, 2 skipped
    Total coverage: 79.67%

## Interfaces and Dependencies

`apps/api/services/collection_service.py`에는 아래 시그니처가 추가되어야 한다.

    @staticmethod
    async def get_collection_status(db: AsyncSession, race_date: str, meet: int) -> dict[str, Any]:
        ...

`apps/api/routers/collection_v2.py`의 `get_collection_status`는 위 메서드를 호출해 `CollectionStatus` DTO로 반환해야 한다.

---

Change note (2026-02-18 / Codex): Milestone 0~3 및 전체 회귀 검증 완료 상태로 문서를 마무리했다. 최종 테스트/커버리지 증거를 Outcomes와 Artifacts에 추가했다.

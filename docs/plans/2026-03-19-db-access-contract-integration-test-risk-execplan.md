# DB 접근 계약 통합 테스트 전환 및 리스크 ExecPlan (후보 F)

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

`PLANS.md` is checked into this repository at `.agent/PLANS.md`. This document must be maintained in accordance with `.agent/PLANS.md`.

## Purpose / Big Picture

이 변경의 목적은 현재 `apps/api`에 공존하는 두 개의 데이터 접근 방식, 즉 SQLAlchemy `AsyncSession` 경로와 `supabase-py` 직접 호출 경로를 하나의 애플리케이션 계약으로 통합할 때 테스트가 붕괴하지 않도록 전환 순서를 고정하는 것이다. 구현이 끝나면 신규 저장소 어댑터를 붙여도 기존 API 응답과 영속화 의미가 유지되는지 공통 계약 테스트로 증명할 수 있어야 하고, deadlock, 성능 저하, transaction 경계 파손, adapter skew를 SQLite가 아니라 실제 Postgres/Supabase 조건에 가까운 테스트로 조기에 잡을 수 있어야 한다.

성공은 다음처럼 관찰한다. 첫째, 동일한 계약 테스트 묶음이 신규 SQLAlchemy 어댑터와 임시 호환 어댑터에서 모두 통과한다. 둘째, `POST /api/v2/jobs`, `GET /api/v2/jobs/{id}`, `POST /api/v2/collection/result`가 adapter 교체 이후에도 같은 HTTP 계약을 유지한다. 셋째, Postgres 전용 통합 테스트가 rollback, upsert, 동시 업데이트, enum/JSONB 동작을 검증하고 SQLite 전용 green을 실제 안전 신호로 오인하지 않게 된다.

## Progress

- [x] (2026-03-19 22:11 KST) `apps/api`의 DB 접근 경로, 테스트 픽스처, 마이그레이션 baseline, coverage 제외 대상을 조사했다.
- [x] (2026-03-19 22:19 KST) 테스트 전환 전략과 리스크 등록부를 포함한 본 ExecPlan 초안을 작성했다.
- [ ] 계약 테스트 스캐폴드 추가. 완료 기준은 `tests/contracts/` 아래에 공통 어댑터 테스트가 생기고 SQLAlchemy 경로가 첫 구현체로 통과하는 것이다.
- [ ] transaction 경계 정리. 완료 기준은 서비스 메서드 내부 `commit()` 난립을 줄이고 unit-of-work 경계가 라우터 또는 작업 runner에서 명시되는 것이다.
- [ ] Postgres/Supabase 전용 통합 테스트 추가. 완료 기준은 deadlock/perf/enum/JSONB 차이를 SQLite와 분리된 마커로 검증하는 것이다.
- [ ] legacy Supabase 직접 경로 shadow 검증 완료. 완료 기준은 `/races` 계열 또는 그 대체 경로가 canonical 모델과 동일한 저장 의미를 갖는지 diff 테스트로 확인하는 것이다.

## Surprises & Discoveries

- Observation: 현재 운영 경로는 이미 SQLAlchemy 중심이지만 legacy `race` 라우터는 `supabase-py` 직접 호출을 유지하고 있다.
  Evidence: `apps/api/routers/jobs_v2.py`, `apps/api/routers/collection_v2.py`, `apps/api/services/job_service.py`, `apps/api/services/collection_service.py`, `apps/api/services/result_collection_service.py`, `apps/api/tasks/async_tasks.py`는 `AsyncSession`을 사용하고, `apps/api/routers/race.py`, `apps/api/services/race_service.py`는 `get_supabase_client()`와 `Client.table(...).execute()`를 직접 사용한다.

- Observation: 현재 테스트 기반은 거의 전부 SQLite in-memory 세션에 기대고 있으며 Supabase 직접 경로는 503 가드 테스트만 있다.
  Evidence: `apps/api/tests/conftest.py`는 `sqlite+aiosqlite:///:memory:`와 `Base.metadata.create_all()`을 사용한다. 반면 Supabase 경로를 직접 검증하는 테스트는 `apps/api/tests/unit/test_race_router_supabase_guard.py` 정도다.

- Observation: coverage 설정이 legacy Supabase 경로를 측정 대상에서 제외하고 있어 전환 중 adapter skew가 수면 아래로 숨을 수 있다.
  Evidence: `apps/api/pytest.ini`의 `coverage:run omit`에는 `infrastructure/supabase_client.py`, `routers/race.py`, `services/race_service.py`가 제외돼 있다.

- Observation: legacy Supabase 경로와 unified schema는 같은 "races/jobs"를 말하지 않는다.
  Evidence: `apps/api/services/race_service.py`는 `collection_jobs`, `races.id`, `races.race_no`, `status`, `race_results`를 전제하지만 `apps/api/migrations/001_unified_schema.sql`과 `apps/api/models/database_models.py`는 `jobs`, `races.race_id`, `races.race_number`, `collection_status`, `result_data`를 canonical로 둔다.

- Observation: transaction 경계가 서비스 내부에 흩어져 있어 계약 통합 시 deadlock과 부분 커밋 리스크가 커진다.
  Evidence: `apps/api/services/job_service.py`, `apps/api/services/collection_service.py`, `apps/api/services/result_collection_service.py`, `apps/api/tasks/async_tasks.py`는 각각 내부에서 `commit()`과 `rollback()`을 수행한다. 특히 task 경로는 `async_session_maker()`로 별도 세션을 열고 서비스도 다시 commit한다.

## Decision Log

- Decision: 테스트 전환의 중심은 "공통 계약 테스트"로 둔다.
  Rationale: 지금처럼 구현체별 단위 테스트만 유지하면 field naming, enum normalization, upsert semantics 차이가 구현체 교체 직전까지 드러나지 않는다.
  Date/Author: 2026-03-19 / Codex.

- Decision: SQLite는 빠른 로컬 회귀용으로 유지하되 DB 계약의 최종 승인 신호로 사용하지 않는다.
  Rationale: SQLite는 Postgres enum, JSONB, row-level locking, pooler, prepared statement, concurrent write behavior를 재현하지 못한다.
  Date/Author: 2026-03-19 / Codex.

- Decision: legacy Supabase 직접 경로는 즉시 삭제하지 않고 shadow adapter로 한 차례 감싼 뒤 제거한다.
  Rationale: 현재 `/races` 계열은 canonical schema와 가장 멀리 떨어져 있으며, 먼저 계약 테스트로 의미 차이를 고정하지 않으면 제거 과정에서 회귀를 판단할 기준이 없다.
  Date/Author: 2026-03-19 / Codex.

- Decision: transaction boundary는 라우터/runner 또는 명시적 unit-of-work에서만 닫히도록 재배치한다.
  Rationale: 서비스 메서드가 개별적으로 commit하면 통합 이후 atomicity를 보장할 수 없고 deadlock 재현 테스트도 불안정해진다.
  Date/Author: 2026-03-19 / Codex.

## Outcomes & Retrospective

현재 시점에서는 구현 전 기준선과 리스크 등록부를 작성했다. 구현이 시작되면 이 섹션에는 최소한 다음을 남긴다. 어떤 계약 인터페이스가 채택됐는지, SQLite 테스트 중 무엇이 contract/postgres 계열로 이동했는지, 실제로 발견된 deadlock 또는 transaction bug가 무엇이었는지, legacy Supabase 경로 제거 여부가 무엇인지다.

## Context and Orientation

이 저장소에서 "DB 접근 계약"은 서비스가 데이터베이스에 무엇을 기대하는지를 표현한 애플리케이션 경계다. 예를 들어 "작업을 생성한다", "경주 결과를 저장한다", "경주를 날짜로 조회한다" 같은 의미가 이에 해당한다. 구현체는 SQLAlchemy일 수도 있고 Supabase SDK일 수도 있지만, 서비스는 이 의미만 알아야 한다.

"어댑터"는 그 계약의 실제 구현체다. 이 저장소의 현재 SQLAlchemy 어댑터 후보는 `AsyncSession` 기반 코드다. 예시는 `apps/api/services/job_service.py`, `apps/api/services/collection_service.py`, `apps/api/services/result_collection_service.py`다. legacy Supabase 어댑터 후보는 `apps/api/services/race_service.py`와 `apps/api/infrastructure/supabase_client.py`다.

"adapter skew"는 두 어댑터가 같은 도메인 개념을 다른 필드명, 다른 enum, 다른 upsert 의미, 다른 오류 모델로 표현하는 현상이다. 이 저장소에서는 `race_id` 대 `id`, `race_number` 대 `race_no`, `collection_status` 대 `status`, `jobs` 대 `collection_jobs`가 대표적이다. 이 차이는 단순 매핑 문제가 아니라 rollback, 중복 삽입, 404/500 분기에도 직접 영향을 준다.

현재 테스트 지형은 세 갈래다. 첫째, `apps/api/tests/conftest.py`가 만드는 SQLite in-memory 기반의 빠른 단위/통합 테스트다. 둘째, `apps/api/tests/unit/test_job_service.py`, `apps/api/tests/unit/test_collection_service.py`, `apps/api/tests/unit/test_auth.py`처럼 `AsyncSession`을 직접 주입하는 서비스 테스트다. 셋째, `apps/api/tests/unit/test_race_router_supabase_guard.py`처럼 Supabase 미설정 가드만 확인하는 제한적 legacy 테스트다. 아직 "같은 계약을 두 어댑터에 적용하는 공통 테스트"는 없다.

## Risk Register

### Deadlock Risk

가장 큰 deadlock 리스크는 통합 과정에서 기존의 산발적 `commit()` 호출을 유지한 채 한 요청 또는 한 작업 안에서 여러 저장소 메서드를 조합하는 경우다. 지금도 `apps/api/services/job_service.py`는 작업 상태 갱신과 로그 적재를 별도 commit으로 나누고, `apps/api/tasks/async_tasks.py`는 별도 세션으로 다시 상태를 바꾼다. 여기에 새 어댑터가 `SELECT ... FOR UPDATE`나 upsert를 도입하면 잠금 순서가 어댑터마다 달라질 수 있다.

이 리스크는 SQLite에서 거의 재현되지 않는다. 따라서 contract 통과 후에도 Postgres 전용 동시성 테스트가 필요하다. 최소 테스트는 "같은 job/race를 두 코루틴이 동시에 갱신할 때 한쪽이 재시도하거나 명시적 충돌을 돌려주는지"를 보는 것이다. 수용 기준은 교착 상태가 영구 대기 없이 종료되고, 실패 시 롤백 후 재시도 가능한 오류 형태를 남기는 것이다.

완화책은 세 가지다. 첫째, 저장소 메서드는 기본적으로 commit하지 않고 변경만 staged 상태로 둔다. 둘째, lock ordering을 문서화한다. 예를 들어 `jobs`를 먼저 잡고 `job_logs` 또는 `race_odds`를 나중에 갱신하도록 고정한다. 셋째, deadlock 재현 테스트를 `pytest.mark.postgres` 또는 동등한 별도 마커로 분리해 CI에서 선택적으로라도 반드시 돌린다.

### Performance Risk

성능 리스크는 계약 통합 이후 추상화 비용보다 "숨겨진 N+1과 row-by-row write"에서 나올 가능성이 높다. 현재 `apps/api/routers/collection_v2.py`는 경주 번호를 순회하면서 서비스 호출을 반복하고, `apps/api/services/collection_service.py`와 `apps/api/services/race_service.py`는 경주 단위 또는 결과 단위로 select 후 update/insert를 반복한다. 통합 시 naïve adapter가 각 메서드마다 새 세션을 만들거나 `.execute()`를 여러 번 발생시키면 수집 배치 시간이 급격히 늘 수 있다.

이 리스크를 잡으려면 "테스트가 성공했다"보다 "쿼리 수와 소요 시간이 예산 안이다"를 같이 봐야 한다. 최소 기준은 동일 입력에서 기존 경로 대비 쿼리 수가 증가하지 않거나, 증가 이유가 문서화돼야 한다는 것이다. Postgres 기준 batch collect와 result collect 각각에 대해 wall-clock 예산과 SQL statement 수를 기록한다. Supabase 직접 경로를 shadow로 유지하는 동안에는 같은 fixture를 두 어댑터에 흘려 저장 횟수와 round-trip 수를 비교한다.

완화책은 bulk upsert 우선, 읽기-수정-쓰기 왕복 최소화, 테스트에서 query counting 계측을 추가하는 것이다. SQLite만으로는 network round-trip과 pooler 비용을 재현할 수 없으므로 perf 게이트는 Postgres/Supabase staging 계열에서만 승인한다.

### Transaction Boundary Risk

transaction 리스크는 현재 서비스들이 "업무 규칙"과 "커밋 시점"을 동시에 소유한다는 점에서 시작한다. `apps/api/services/result_collection_service.py`는 결과 저장 후 commit하고 이어서 배당 적재를 또 commit한다. `apps/api/services/collection_service.py`도 여러 helper가 내부 commit을 갖고 있다. 이런 상태에서 계약 통합으로 저장소 인터페이스만 도입하면 겉보기 추상화는 생기지만 atomicity는 여전히 깨져 있어 부분 성공 상태가 늘어난다.

테스트 전환의 핵심은 이 리스크를 명시적 acceptance로 올리는 것이다. 신규 contract 테스트에는 "중간 단계에서 예외가 나면 race/result/job 상태가 모두 원복되는가"를 넣어야 한다. 예를 들어 결과 수집이 성공했지만 odds 저장이 실패하는 시나리오에서 어떤 필드는 commit되고 어떤 필드는 rollback되어야 하는지 먼저 문서로 결정하고, 그 결정 그대로 양 어댑터에 같은 테스트를 적용한다.

완화책은 unit-of-work 경계를 도입하고 서비스 내부 commit을 제거하는 것이다. 라우터, background runner, 또는 명시적 application service가 한 번만 commit하도록 만들면 rollback 테스트가 단순해지고 adapter 간 의미 차이도 줄어든다.

### Adapter Skew Risk

adapter skew는 이 작업의 핵심 리스크다. legacy Supabase 경로는 `collection_jobs`와 `race_results`를 중심으로 사고하고, unified SQLAlchemy 경로는 `jobs`, `job_logs`, `races.result_data`를 중심으로 사고한다. 같은 "결과 수집"도 한쪽은 별도 테이블을 쓰고 다른 쪽은 `races` 행 내부 JSONB를 갱신한다. 같은 "경주 식별자"도 한쪽은 `id`를, 다른 쪽은 `race_id`를 쓴다.

이 차이를 방치하면 테스트는 녹색인데 실제 데이터 의미는 달라지는 상황이 생긴다. 예를 들어 라우터 응답은 같아 보여도 필수 필드가 누락되거나, 이후 단계가 찾는 row key가 달라져 재수집과 중복 삽입이 발생할 수 있다. 이 리스크 때문에 characterization test와 contract test를 분리해야 한다. characterization test는 "지금 사용자가 보는 동작"을 고정하고, contract test는 "새 canonical 계약"을 고정한다. 둘 다 통과할 때만 legacy 제거가 가능하다.

완화책은 canonical DTO와 canonical persistence shape를 먼저 선언하는 것이다. 어댑터는 각자 내부 필드명을 써도 되지만 외부 계약에서는 `race_id`, `date`, `meet`, `race_number`, `collection_status`, `result_data`, `job_id`, `job_type`, `job_status`만 허용한다. legacy 필드명은 adapter 내부에서만 매핑한다.

## Plan of Work

첫 단계는 현재 동작을 얼리는 characterization test 추가다. 여기서는 구현체를 추상화하지 않는다. 대신 `apps/api/tests/unit/test_job_service.py`, `apps/api/tests/unit/test_collection_service.py`, `apps/api/tests/integration/test_jobs_v2_router_additional.py`, `apps/api/tests/unit/test_race_router_supabase_guard.py`를 기준선으로 삼고, `/races` legacy 응답과 `/api/v2/jobs`, `/api/v2/collection/result` canonical 응답을 각각 "사용자 계약" 관점에서 보강한다. 이 단계의 목표는 리팩터링 전후 diff를 판단할 관찰 창을 확보하는 것이다.

둘째 단계는 공통 계약 테스트 하네스를 만든다. `apps/api/tests/contracts/` 아래에 `test_job_store_contract.py`, `test_race_store_contract.py`, `test_api_key_store_contract.py` 같은 공용 테스트를 두고, 각 테스트는 "adapter factory"만 바꿔서 실행되게 만든다. 첫 구현체는 SQLAlchemy 기반 adapter다. 두 번째 구현체는 legacy Supabase adapter 또는 그에 준하는 compatibility shim이다. 이 단계에서 서비스 단위 테스트는 `AsyncSession` 직접 주입보다 store contract double 주입으로 이동하기 시작한다.

셋째 단계는 transaction 경계를 재배치하면서 테스트를 이동한다. 서비스 메서드 안의 `commit()`을 제거하거나 최소화하고, commit/rollback을 책임지는 `UnitOfWork` 또는 동등한 경계를 도입한다. 이후 `apps/api/tests/unit/test_job_service.py`와 `apps/api/tests/unit/test_collection_service.py`는 ORM 세부 대신 "예외가 나면 commit이 일어나지 않는가", "성공 시 한 번만 flush/commit 되는가"를 검증하도록 고친다. 동시에 `apps/api/tests/integration/`에는 실제 DB에 대해 atomicity를 보는 테스트를 추가한다.

넷째 단계는 Postgres/Supabase 전용 검증을 붙인다. 이 단계에서 SQLite는 빠른 회귀용으로 남아도 되지만 승인은 Postgres 계열 테스트가 한다. unified migration을 올린 실제 Postgres 테스트 데이터베이스에서 enum, JSONB, upsert, 동시 업데이트, pooler 환경을 검증한다. legacy Supabase 직접 경로를 유지하는 기간에는 동일 fixture를 양쪽에 흘려 저장 결과를 비교하는 shadow diff 테스트를 둔다.

마지막 단계는 legacy 제거다. 모든 characterization test와 contract test와 Postgres 통합 테스트가 통과하면 `/races` legacy 라우터와 `services/race_service.py`를 제거하거나 canonical 저장소를 사용하는 thin compatibility layer로 축소한다. 제거 직전에는 coverage 제외 목록에서 legacy 모듈을 잠시 복원해 마지막 한 번 전체 회귀를 본다.

## Concrete Steps

모든 명령은 저장소 루트 `/Users/chsong/Developer/Personal/kra-analysis`에서 실행한다.

1. 현재 기준선 확인.

    cd apps/api
    uv run pytest -q tests/unit/test_job_service.py tests/unit/test_collection_service.py tests/unit/test_auth.py tests/integration/test_jobs_v2_router_additional.py tests/unit/test_race_router_supabase_guard.py

   기대 결과는 현재 SQLAlchemy 경로와 Supabase guard 경로의 baseline이 녹색이며, 둘이 같은 계약을 검증하는 것은 아니라는 사실을 확인하는 것이다.

2. coverage/스키마 drift 근거 확인.

    cd apps/api
    sed -n '1,220p' pytest.ini
    sed -n '1,220p' migrations/001_unified_schema.sql
    sed -n '1,220p' services/race_service.py

   기대 결과는 legacy 경로가 coverage 제외이며 unified schema와 다른 테이블/컬럼을 전제한다는 점을 눈으로 확인하는 것이다.

3. 계약 테스트 스캐폴드 추가 후 빠른 검증.

    cd apps/api
    uv run pytest -q tests/contracts

   기대 결과는 초기에는 SQLAlchemy adapter만 연결해도 되고, 이후 Supabase compatibility adapter가 같은 테스트를 통과해야 한다.

4. Postgres 계열 transaction/deadlock 검증.

    cd apps/api
    TEST_DATABASE_URL=postgresql+asyncpg://... uv run pytest -q -m "postgres and db_contract"

   기대 결과는 SQLite가 아니라 Postgres에서 rollback, upsert, concurrent update 테스트가 실행되는 것이다. deadlock이 발생하면 영구 hang 대신 실패 로그와 재현 가능한 테스트 이름이 남아야 한다.

5. shadow diff 검증.

    cd apps/api
    TEST_DATABASE_URL=postgresql+asyncpg://... uv run pytest -q tests/shadow

   기대 결과는 같은 입력 fixture에 대해 legacy adapter와 canonical adapter의 저장 의미 차이가 보고서로 드러나는 것이다.

## Validation and Acceptance

테스트 전환 전략의 acceptance는 단순히 "테스트 파일이 많아졌다"가 아니다. 첫째, 서비스 계층 테스트의 주된 더블이 `AsyncSession` 또는 raw Supabase client가 아니라 DB 계약 인터페이스가 되어야 한다. 둘째, 최소 한 종류의 저장소 계약 테스트가 두 구현체에서 모두 통과해야 한다. 셋째, Postgres 계열 테스트가 transaction rollback과 concurrent update를 실제로 검증해야 한다. 넷째, legacy 모듈이 coverage 제외 목록에 있어도 shadow diff 또는 characterization test로 의미 차이를 잡을 수 있어야 한다.

리스크 acceptance는 다음과 같다. deadlock 리스크는 동시 갱신 테스트가 영구 대기 없이 종료될 때만 수용된다. 성능 리스크는 batch collect/result collect에서 쿼리 수 또는 round-trip 수가 baseline 대비 통제 가능할 때만 수용된다. transaction 리스크는 중간 실패 시 partial commit이 의도한 범위 밖으로 퍼지지 않을 때만 수용된다. adapter skew 리스크는 canonical DTO/persistence shape로 비교했을 때 의미 차이가 0이거나, 남는 차이가 명시적 compatibility note로 문서화될 때만 수용된다.

## Idempotence and Recovery

테스트 데이터베이스는 unified migration 기준으로 반복 생성과 파기가 가능해야 한다. contract 테스트는 각 테스트가 자기 데이터를 스스로 만들고 정리하도록 작성해 순서 의존성을 없앤다. shadow diff 테스트는 legacy와 canonical을 같은 실DB에 동시에 쓰지 말고, 서로 분리된 schema 또는 분리된 데이터베이스에서 실행한다.

transaction 리팩터링이 중간에 멈추면 가장 먼저 해야 할 일은 서비스 내부 `commit()` 제거 범위를 문서와 `Progress`에 반영하는 것이다. 이후 실패한 테스트를 고치기 전에 기존 baseline characterization test를 다시 녹색으로 돌려 계약 붕괴가 없음을 확인한다.

## Artifacts and Notes

이번 계획 수립에서 직접 근거로 읽은 파일은 다음과 같다.

    apps/api/tests/conftest.py
    apps/api/pytest.ini
    apps/api/infrastructure/database.py
    apps/api/infrastructure/supabase_client.py
    apps/api/models/database_models.py
    apps/api/migrations/001_unified_schema.sql
    apps/api/routers/jobs_v2.py
    apps/api/routers/collection_v2.py
    apps/api/routers/race.py
    apps/api/services/job_service.py
    apps/api/services/collection_service.py
    apps/api/services/result_collection_service.py
    apps/api/services/race_service.py
    apps/api/tasks/async_tasks.py
    apps/api/tests/unit/test_job_service.py
    apps/api/tests/unit/test_collection_service.py
    apps/api/tests/unit/test_auth.py
    apps/api/tests/unit/test_race_router_supabase_guard.py
    apps/api/tests/integration/test_jobs_v2_router_additional.py

이 문서는 구현 전 하위 계획이다. 실제 구현을 시작하면 신규 테스트 파일 이름, 추가된 마커 이름, Postgres 검증 커맨드, 제거된 legacy 경로를 이 섹션과 `Progress`에 즉시 반영한다.

## Interfaces and Dependencies

이 계획이 끝날 때 최소한 다음 인터페이스 성질이 존재해야 한다.

`apps/api/services/contracts/db_access.py` 또는 동등한 위치에는 job/race/api key 접근을 표현하는 명시적 프로토콜이 있어야 한다. 이름은 달라도 되지만 의미는 다음과 같아야 한다. `JobStore`는 작업 생성, 단건 조회, 목록 조회, 상태 전이, 로그 적재를 제공한다. `RaceStore`는 경주 기본 정보 upsert, 결과 저장, 배당 저장, 날짜별 조회를 제공한다. `APIKeyStore`는 키 조회와 사용 가능성 판단을 제공한다.

이 인터페이스는 canonical 필드명만 외부에 노출해야 한다. 경주 식별자는 `race_id`, 순번은 `race_number`, 수집 상태는 `collection_status`, 결과는 `result_data`다. 작업 식별자는 `job_id`, 작업 유형은 canonical `job_type`, 작업 상태는 canonical `job_status`다. legacy `id`, `race_no`, `status`, `collection_jobs` 같은 표현은 adapter 내부 번역 계층에서만 허용한다.

transaction 책임을 표현하는 `UnitOfWork` 또는 동등한 경계가 필요하다. 이 경계는 `commit()`과 `rollback()`을 소유하고, 서비스 메서드는 저장 의미만 기술한다. background runner인 `apps/api/tasks/async_tasks.py`와 라우터 계층은 이 경계를 사용해 한 요청 또는 한 작업당 한 번의 transaction 종료 시점을 갖게 해야 한다.

테스트 계층에는 최소 세 종류의 마커가 필요하다. 빠른 회귀를 위한 `unit`, 공통 저장소 의미를 검증하는 `contract`, 실제 Postgres/Supabase 조건을 검증하는 `postgres` 또는 동등 마커다. 필요하면 `shadow`와 `perf`를 추가할 수 있지만, 핵심은 SQLite green과 Postgres green을 명확히 분리하는 것이다.

Change note: 2026-03-19 / Codex. DB 접근 계약 통합 작업을 병렬 계획으로 분해하기 위해 테스트 전환 전략과 리스크 등록부를 별도 ExecPlan로 작성했다. 이유는 메인 아키텍처 계획과 독립적으로 후보 F 범위를 실행·검토할 수 있게 하기 위해서다.

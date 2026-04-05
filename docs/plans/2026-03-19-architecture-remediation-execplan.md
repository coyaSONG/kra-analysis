# 플랫폼 안정화 및 계약 통일 ExecPlan

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

`PLANS.md` is checked into this repository at `.agent/PLANS.md`. This document must be maintained in accordance with `.agent/PLANS.md`.

## Purpose / Big Picture

이 변경의 목표는 현재 `apps/api` 런타임을 "작동은 하지만 계약이 분열된 상태"에서 "운영 가능한 단일 계약 시스템"으로 정리하는 것이다. 구현이 완료되면 사용자는 Redis가 없어도 `/health/detailed`에서 일관된 `degraded` 상태를 확인할 수 있고, `jobs` API는 하나의 작업 타입 vocabulary를 사용하며, 새 환경에서는 마이그레이션 한 번으로 현재 코드와 맞는 스키마가 준비된다. 문서도 실제 런타임인 `main_v2:app`을 기준으로 정리되어 신규 기여자가 잘못된 구조를 학습하지 않게 된다.

결과는 다음 행동으로 검증한다. 첫째, Redis를 일부러 끈 상태에서 API를 띄우고 `/health/detailed`를 호출하면 HTTP 200과 `degraded` 응답을 본다. 둘째, `POST /api/v2/jobs`와 `GET /api/v2/jobs/{id}`가 같은 작업 타입 집합을 사용한다. 셋째, 비어 있는 데이터베이스에서 마이그레이션만 적용해도 앱이 정상 기동하고 테스트가 통과한다. 넷째, README와 API 문서가 현재 존재하는 파일과 명령만 설명한다.

## Progress

- [x] (2026-03-19 21:37 KST) 코드베이스 정적 분석과 병렬 서브에이전트 검토를 바탕으로 주요 결함군을 정리했다.
- [x] (2026-03-19 21:37 KST) `docs/plans/2026-03-19-architecture-remediation-execplan.md` 초안을 작성했다.
- [x] (2026-03-19 21:52 KST) 루트 `README.md`, `apps/api/README.md`, `docs/project-overview.md`, `packages/scripts/README.md`, `apps/api/docs/SUPABASE_SETUP.md`를 현재 `apps/api` 중심 구조에 맞게 갱신했다.
- [ ] P0 문서 기준선 확정. 완료 기준은 이 문서와 후속 수정이 실제 런타임, 실제 스키마, 실제 CI 경로를 기준으로 설명하는 것이다. 남은 범위는 세부 운영 문서와 코드 패치 후 결과 반영이다.
- [ ] P1 런타임 안전화 패치. 범위는 health, logging, auth, DTO/job type 계약 정리다.
- [ ] P2 스키마 source of truth 일원화. 범위는 active migration chain 정리, verifier 재작성, `create_all()` 사용 정책 수정이다.
- [ ] P3 job runner 경계 명시화. 범위는 in-process runner 추상화, 운영 모드 제약 문서화, 후속 durable runner 전환 준비다.
- [ ] P4 collection 도메인 정리와 문서 드리프트 해소. 범위는 `CollectionService` 책임 축소와 README/API 문서 갱신이다.
- [ ] 전체 회귀 테스트, 로컬 기동 검증, 문서 최종 업데이트.

## Surprises & Discoveries

- Observation: 앱 시작은 Redis 초기화 실패를 허용하지만 상세 헬스체크는 Redis dependency 예외로 먼저 깨질 수 있다.
  Evidence: `apps/api/main_v2.py`의 startup 경로와 `apps/api/routers/health.py`, `apps/api/infrastructure/redis_client.py`의 `get_redis()` 호출 경로가 충돌한다.

- Observation: 작업 타입은 DB/DTO와 dispatcher가 서로 다른 vocabulary를 사용한다.
  Evidence: `apps/api/models/database_models.py`, `apps/api/models/job_dto.py`는 `batch|collection|...`를 사용하지만 `apps/api/services/job_service.py`는 `batch_collect|collect_race|...`를 사용한다.

- Observation: 마이그레이션 기준 스키마가 둘 이상이며 verifier는 현재 unified schema가 아니라 legacy schema를 정답처럼 본다.
  Evidence: `apps/api/migrations/001_initial_schema.sql`, `apps/api/migrations/001_unified_schema.sql`, `apps/api/scripts/apply_migrations.py`가 서로 다른 테이블 집합을 전제한다.

- Observation: 실제 운영에 등록된 로깅 미들웨어와 테스트가 검증하는 로깅 미들웨어가 다르다.
  Evidence: `apps/api/main_v2.py`는 `RequestLoggingMiddleware`를 등록하지만 `apps/api/tests/unit/test_middleware_logging.py` 계열 테스트는 `LoggingMiddleware` 계약을 중심으로 작성되어 있다.

- Observation: `CollectionService`는 수집, 상세 fan-out, 저장, 전처리, 보강, 배당 수집을 한 클래스에 동시에 담고 있다.
  Evidence: `apps/api/services/collection_service.py` 하나에 여러 단계의 orchestration과 persistence policy가 집중돼 있다.

- Observation: README뿐 아니라 `packages/scripts/README.md`도 현재 디렉터리 구조가 아니라 과거 `race_collector` 중심 구조를 설명하고 있었다.
  Evidence: 실제 `packages/scripts`에는 `evaluation`, `prompt_improvement`, `ml`, `autoresearch`, `archive`가 존재하지만 문서는 삭제된 하위 디렉터리와 Node 수집 스크립트를 설명하고 있었다.

## Decision Log

- Decision: 이 리메디에이션은 새 기능 추가보다 "단일 계약 회복"을 우선한다.
  Rationale: 현재 장애와 유지보수 비용의 대부분은 미구현 기능보다 서로 충돌하는 계약과 문서 드리프트에서 발생한다.
  Date/Author: 2026-03-19 / Codex.

- Decision: 첫 산출물은 코드보다 문서다. 구체적으로 이 ExecPlan을 canonical 실행 문서로 만든 뒤, 이후 패치는 이 문서를 갱신하면서 진행한다.
  Rationale: 범위가 넓고 결함군이 얽혀 있어 선후관계와 acceptance를 먼저 고정하지 않으면 부분 수정이 다시 드리프트를 만든다.
  Date/Author: 2026-03-19 / Codex.

- Decision: active schema baseline은 legacy가 아니라 unified 계열을 기준으로 정리한다.
  Rationale: 현재 API 구조는 `jobs`, `job_logs`, `api_keys`, `prompt_templates`가 있는 unified 모델에 더 가깝고, legacy baseline은 현재 운영 경로와 어긋난다.
  Date/Author: 2026-03-19 / Codex.

- Decision: job runner는 단기적으로 추상화와 운영 제약 문서화부터 수행하고, durable queue 전환은 그 다음 단계로 둔다.
  Rationale: 현재 가장 큰 즉시 리스크는 runner interface 부재와 운영 가정 불일치이며, 바로 외부 큐를 도입하면 범위가 급격히 커진다.
  Date/Author: 2026-03-19 / Codex.

## Outcomes & Retrospective

현재 시점에서는 구현 전 기준선 문서만 작성했다. 성공적인 완료 시 이 섹션에는 최소한 다음 내용을 남긴다. Redis 미초기화 시 health 동작 결과, migration only 기동 성공 여부, job type vocabulary 통일 결과, 문서-코드 drift 제거 범위, 그리고 남은 후속 과제다.

## Context and Orientation

이 저장소는 겉보기에는 monorepo지만 실제 운영 코어는 `apps/api`다. 진입점은 `apps/api/main_v2.py`이며, 여기서 라우터, 미들웨어, 데이터베이스 초기화, Redis 초기화를 연결한다. `router`는 HTTP 요청과 응답만 다루는 API 계층이고, `service`는 업무 규칙과 orchestration을 담는 계층이다. 이 저장소에서는 `apps/api/services/collection_service.py`와 `apps/api/services/job_service.py`가 대표적인 service다.

"source of truth"는 어떤 데이터 구조나 계약의 최종 기준이 되는 하나의 정의를 뜻한다. 현재 이 저장소에는 작업 타입, 마이그레이션 체인, 로깅 계약, API 문서의 source of truth가 각각 둘 이상 존재한다. 예를 들어 작업 타입은 DB 모델과 서비스 디스패처가 다른 이름 집합을 쓰고 있고, 스키마는 `create_all()`과 여러 SQL 마이그레이션 파일과 검증 스크립트가 서로 다른 세계를 설명한다.

"degraded health"는 전체 서비스가 완전히 죽지 않았지만 일부 의존성이 빠진 상태를 명시적으로 보여주는 헬스 응답이다. 이 저장소에서는 Redis가 대표 사례다. 앱은 Redis 없이도 떠야 한다는 설계를 갖고 있지만, 실제 상세 헬스체크는 현재 그 설계를 일관되게 반영하지 못한다.

핵심 파일은 다음과 같다. `apps/api/main_v2.py`는 런타임 wiring의 중심이다. `apps/api/routers/health.py`와 `apps/api/routers/metrics.py`는 운영 상태 노출 경로다. `apps/api/dependencies/auth.py`는 API key 인증과 권한 검사를 구현한다. `apps/api/models/database_models.py`, `apps/api/models/job_dto.py`, `apps/api/models/collection_dto.py`는 DB/API 계약을 정의한다. `apps/api/services/job_service.py`, `apps/api/infrastructure/background_tasks.py`, `apps/api/tasks/async_tasks.py`는 작업 실행 경로를 이룬다. `apps/api/infrastructure/database.py`, `apps/api/migrations/*.sql`, `apps/api/scripts/apply_migrations.py`는 스키마와 초기화 경로를 결정한다. `README.md`, `apps/api/README.md`, `apps/api/docs/SUPABASE_SETUP.md`, `docs/project-overview.md`는 현재 드리프트가 확인된 대표 문서다.

## Plan of Work

이 작업은 문서부터 시작하지만 최종 목표는 코드와 문서가 같은 사실을 말하게 만드는 것이다. 첫 단계에서는 이 ExecPlan을 기준 문서로 추가하고, 기존 문서 중 실제 런타임과 어긋나는 설명을 표시하거나 정정한다. 이 단계의 목적은 신규 기여자가 오래된 README를 보고 잘못된 구조를 학습하지 않게 만드는 것이다.

다음 단계에서는 런타임 안전화 패치를 수행한다. `apps/api/routers/health.py`에서 Redis dependency를 optional 경로로 바꾸고, `apps/api/infrastructure/redis_client.py`의 예외를 상세 헬스체크가 흡수하도록 수정한다. `apps/api/main_v2.py`와 `apps/api/middleware/logging.py`에서는 실제 운영에 사용할 로깅 미들웨어를 하나로 고정하고 request id, redaction, body logging 정책을 동일한 코드 경로로 통합한다. `apps/api/dependencies/auth.py`에서는 API key 반환 타입과 권한 검사 함수의 기대 타입을 맞춘다. `apps/api/models/job_dto.py`, `apps/api/models/database_models.py`, `apps/api/services/job_service.py`, 관련 라우터에서는 작업 타입 vocabulary를 하나로 통일한다. `apps/api/models/collection_dto.py`와 `apps/api/routers/collection_v2.py`에서는 미구현 옵션을 제거하거나 명시적으로 unsupported 처리한다.

그 다음 단계에서는 스키마 기준선을 정리한다. `apps/api/migrations/001_unified_schema.sql`을 현재 active baseline으로 확정하고, `apps/api/migrations/001_initial_schema.sql`은 active chain에서 제외한다. `apps/api/scripts/apply_migrations.py`는 단순 glob runner가 아니라 버전 추적과 현재 unified schema 검증을 수행하는 스크립트로 바꾼다. `apps/api/infrastructure/database.py`에서는 `create_all()`을 production path에서 제거하거나 개발 환경 전용으로 제한한다. 이 단계가 끝나면 새 데이터베이스에 대해 "migration only" 부트스트랩이 가능해야 한다.

그 다음 단계에서는 job runner 경계를 명시한다. `apps/api/infrastructure/background_tasks.py` 앞에 runner interface를 두고 `apps/api/services/job_service.py`가 구현 세부 대신 interface에 의존하게 만든다. 이 문서의 범위에서는 바로 외부 큐를 도입하지 않는다. 대신 현재 in-process runner가 단일 인스턴스 전제라는 사실을 코드와 문서에 명시하고, 이후 durable runner로 바꾸기 쉬운 경계를 먼저 만든다.

마지막 단계에서는 collection 도메인과 문서를 정리한다. `apps/api/services/collection_service.py`를 수집 orchestration, 상세 수집, 데이터 저장, 전처리/보강으로 분해할 준비를 하고, 문서에서는 `basic_data`, `result_data`, `enriched_data`의 의미를 현재 코드 기준으로 설명한다. 동시에 `README.md`, `apps/api/README.md`, `docs/project-overview.md`를 현재 런타임과 CI에 맞게 갱신한다.

## Concrete Steps

모든 명령은 저장소 루트 `/Users/chsong/Developer/Personal/kra-analysis`에서 실행한다.

1. 문서 기준선 추가와 드리프트 확인.

    sed -n '1,220p' .agent/PLANS.md
    sed -n '1,220p' docs/plans/2026-03-19-architecture-remediation-execplan.md
    sed -n '1,220p' README.md
    sed -n '1,220p' apps/api/README.md

   기대 결과는 새 ExecPlan이 존재하고, README류 문서의 obsolete 설명이 이후 수정 대상임을 확인하는 것이다.

2. 런타임 안전화 대상 테스트 작성 또는 보강.

    cd apps/api
    uv run pytest -q tests/unit/test_health_detailed_branches.py
    uv run pytest -q tests/unit/test_middleware_logging.py
    uv run pytest -q tests/services/test_job_service.py

   기대 결과는 현재 상태에서 일부 테스트가 실제 wiring mismatch를 충분히 잡지 못함을 확인하고, 필요한 새 테스트 이름을 이 문서와 코드에 기록하는 것이다.

3. 스키마 기준선 정합성 점검.

    cd apps/api
    uv run python scripts/apply_migrations.py --help
    uv run python - <<'PY'
    from models.database_models import Job
    print(sorted(c.name for c in Job.__table__.columns))
    PY

   기대 결과는 migration script와 ORM이 같은 스키마를 설명하지 않는 지점을 확인하는 것이다.

4. API 회귀 테스트 실행.

    pnpm -F @apps/api test

   기대 결과는 문서 수정만으로는 테스트 상태가 바뀌지 않으며, 이후 코드 패치 단계에서 회귀 기준으로 사용할 수 있는 baseline을 확보하는 것이다.

5. 로컬 기동 및 수동 확인.

    cd apps/api
    uv run uvicorn main_v2:app --reload

   기대 결과는 서버가 뜨고, 후속 코드 패치 이후 `curl http://127.0.0.1:8000/health/detailed`와 `curl http://127.0.0.1:8000/metrics`로 관찰 가능한 acceptance를 확보하는 것이다.

## Validation and Acceptance

문서 단계 완료의 acceptance는 "이 문서만 읽고도 다음 구현자가 무엇을 왜 어떤 순서로 바꿔야 하는지 이해할 수 있는가"다. 구체적으로 다음을 만족해야 한다.

첫째, Redis health 문제, job type 분열, schema baseline 충돌, logging/auth wiring mismatch, collection service 비대화, 문서 드리프트가 각각 어느 파일에서 발생하는지 이 문서에 명시돼 있어야 한다. 둘째, 각 결함군마다 수정 파일과 관찰 가능한 검증 방법이 적혀 있어야 한다. 셋째, 구현 단계로 넘어가면 이 문서를 갱신하면서 진행할 수 있어야 한다.

코드 패치 단계의 최종 acceptance는 다음 행동으로 검증한다. Redis를 끈 상태에서 `/health/detailed`가 HTTP 200과 `degraded`를 반환한다. `POST /api/v2/jobs`와 `GET /api/v2/jobs/{id}`가 같은 작업 타입 집합을 사용한다. 빈 DB에서 migration만 적용해도 앱이 기동한다. 실제 앱에 등록된 로깅 미들웨어와 테스트 대상 미들웨어가 동일하다. README와 API 문서가 존재하지 않는 앱이나 레거시 Celery 경로를 설명하지 않는다.

## Idempotence and Recovery

이 문서 작성 단계는 반복 실행해도 안전하다. 이후 구현 단계에서는 각 milestone을 additive change로 진행하고, 테스트가 초록색일 때만 다음 단계로 넘어간다. 마이그레이션 체계 정리처럼 실패 비용이 큰 작업은 새 빈 데이터베이스에서 먼저 검증한 뒤 기존 데이터베이스에 적용한다. legacy와 unified 테이블이 동시에 보이는 mixed state는 자동 수정하지 말고 즉시 중단한 뒤 별도 전환 절차를 추가로 문서화한다.

문서 수정은 언제든 재시도할 수 있다. 코드 패치가 중간에 멈추면 이 문서의 `Progress`, `Surprises & Discoveries`, `Decision Log`를 먼저 실제 상태로 갱신한 뒤 재개한다.

## Artifacts and Notes

이번 문서화 단계에서 핵심 근거로 사용한 파일은 다음과 같다.

    apps/api/main_v2.py
    apps/api/routers/health.py
    apps/api/infrastructure/redis_client.py
    apps/api/dependencies/auth.py
    apps/api/models/database_models.py
    apps/api/models/job_dto.py
    apps/api/models/collection_dto.py
    apps/api/services/job_service.py
    apps/api/services/collection_service.py
    apps/api/infrastructure/background_tasks.py
    apps/api/migrations/001_initial_schema.sql
    apps/api/migrations/001_unified_schema.sql
    apps/api/scripts/apply_migrations.py
    README.md
    apps/api/README.md
    docs/project-overview.md

이 문서는 현재 분석 결과를 바탕으로 작성한 첫 기준선이다. 구현이 시작되면 각 milestone 종료 시 `Progress`와 `Outcomes & Retrospective`를 반드시 갱신한다.

## Interfaces and Dependencies

이 계획이 끝날 때 다음 인터페이스 성질이 보장되어야 한다.

`apps/api/routers/health.py`는 Redis client가 없더라도 상세 헬스 응답을 생성할 수 있어야 한다. 이는 optional dependency 또는 내부 status probe 함수 형태로 구현할 수 있지만, 최종 동작은 "예외를 500으로 내보내지 않고 degraded 상태를 보고"하는 것이다.

`apps/api/dependencies/auth.py`는 인증 함수와 권한 함수가 같은 타입 계약을 공유해야 한다. 최종 구현에서는 API key 문자열만 사용할지, `APIKey` ORM 객체를 사용할지 하나로 결정해야 하며 두 경로를 혼합하지 않는다.

`apps/api/services/job_service.py`와 관련 DTO/ORM은 하나의 작업 타입 enum 또는 동등한 단일 집합을 사용해야 한다. DB, API, 서비스, 문서가 같은 이름을 써야 하며 alias는 임시 호환 경로일 때만 명시적으로 유지한다.

`apps/api/scripts/apply_migrations.py` 또는 이를 대체하는 migration runner는 version tracking과 canonical schema verification을 제공해야 한다. 최종 상태에서는 unified baseline을 기준으로 새 DB를 준비할 수 있어야 하며 `create_all()`은 production source of truth가 아니어야 한다.

`apps/api/services/collection_service.py`는 최종적으로 더 작은 서비스로 분해될 수 있어야 하며, 최소한 데이터 단계의 의미가 문서와 코드에서 같은 말을 해야 한다.

Change note: 2026-03-19에 현재 코드베이스 정적 분석 결과를 바탕으로 최초 ExecPlan을 추가했다. 이후 같은 날 루트/API/프로젝트 개요/스크립트/Supabase 문서를 현재 `apps/api` 중심 구조에 맞게 정리하고 Progress와 Discoveries를 갱신했다. 이유는 광범위한 리메디에이션 작업을 문서 우선으로 정리하고 이후 패치의 기준선을 고정하기 위해서다.

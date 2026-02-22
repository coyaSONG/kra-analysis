# 90일 아키텍처 고도화 ExecPlan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

`PLANS.md` is checked into this repository at `.agent/PLANS.md`. This document must be maintained in accordance with `.agent/PLANS.md`.

## Purpose / Big Picture

이 변경의 목표는 현재 프로젝트를 “개발 중심 구조”에서 “운영 가능한 프로덕션 구조”로 올리는 것이다. 구현이 완료되면, 장시간 수집/분석 작업이 API 프로세스 재시작에 영향을 받지 않고 지속되며, 보안 기본선(TLS 검증, 민감정보 마스킹, 의존성 취약점 검사)이 CI에서 강제된다. 또한 관측성(추적/메트릭/로그 상관관계)과 실험 추적(MLflow run 표준화)이 도입되어 운영 장애와 모델 품질 저하를 같은 주기 안에서 진단할 수 있다.

사용자는 다음 행동으로 결과를 확인할 수 있다. 첫째, `POST /api/v2/jobs` 이후 생성된 작업이 API 재시작 이후에도 상태를 유지한다. 둘째, `/metrics`와 `/health/detailed`에서 실제 의존성 상태가 일관되게 노출된다. 셋째, 프롬프트 평가 실행 시 run 메타데이터(커밋 SHA, 데이터 스냅샷, 프롬프트 버전)가 MLflow에 남아 동일 조건 재현이 가능해진다.

## Progress

- [x] (2026-02-21 22:59 KST) 레포의 현재 구조와 운영 리스크를 재검토하고 90일 범위를 확정했다.
- [x] (2026-02-21 23:00 KST) `docs/plans/2026-02-21-architecture-hardening-90day-execplan.md` 초안을 작성했다.
- [x] (2026-02-21 23:13 KST) Task 1 완료: `KRA_API_VERIFY_TLS` 플래그 도입, `verify=False` 하드코딩 제거, TLS 정책 테스트 추가.
- [x] (2026-02-21 23:24 KST) Task 2 완료: 요청 바디 민감정보 마스킹 및 대용량 요청 바디 미리읽기 방지, 관련 테스트 추가.
- [x] (2026-02-21 23:38 KST) Task 3 완료: Python 보안 CI(report/gate) 도입 및 baseline 기반 pip-audit 게이트 구현.
- [x] (2026-02-21 23:58 KST) Task 4 완료: `/metrics` 도입, HTTP 메트릭 수집, `/health/detailed` background task 실상태 반영.
- [x] (2026-02-22 00:10 KST) Task 5 완료: `JobRunner` 추상화 도입, `JobService` 주입 구조 전환, 관련 테스트 갱신.
- [x] (2026-02-22 01:05 KST) Task 6 완료: Celery app/task/runner 구현, `JOB_RUNNER_MODE` 플래그 연결, dev worker compose 및 eager 모드 통합 테스트 추가.
- [x] (2026-02-22 01:42 KST) Task 7 완료: Alembic 마이그레이션 체계 도입, startup `create_all` 비개발 비활성화, CI `alembic upgrade head` 검증 단계 추가.
- [x] (2026-02-22 02:05 KST) Task 8 완료: 평가/개선 루프 공통 `run_metadata` 스키마 도입, MLflow/로컬 아티팩트 동시 기록, 관련 테스트 추가.
- [x] (2026-02-22 14:40 KST) Task 9 완료: `docs/operations/slo.md`, `docs/operations/runbook.md` 작성 및 운영 온보딩 링크를 README/API README에 반영.
- [x] (2026-02-22 14:47 KST) Task 10 완료: 루트 `README.md`, `docs/project-overview.md`를 현재 구조(`apps/api`, `packages/*`) 기준으로 정합화하고 obsolete 명령 제거.
- [x] Phase 1(1~30일): 보안/관측성 기본선 구현.
- [x] Phase 2(31~60일): Durable Job 아키텍처 전환(Task 5~7 완료).
- [x] Phase 3(61~90일): 실험/데이터 운영 표준화 및 SLO 운영 고도화(Task 8~10 완료).
- [ ] 전체 회귀 테스트, 부하 점검, 운영 문서 최종 업데이트.

## Surprises & Discoveries

- Observation: README는 `apps/collector`를 포함한 구조를 설명하지만 현재 워크트리에는 `apps/api`만 존재한다.
  Evidence: `README.md`의 구조 설명과 `ls apps` 결과 불일치.

- Observation: 설정에는 `prometheus_enabled`가 있으나 실제 애플리케이션에서 메트릭 노출 코드가 연결되어 있지 않다.
  Evidence: `apps/api/config.py`에 옵션 존재, 런타임 라우트/미들웨어에 `/metrics` 처리 없음.

- Observation: 배경 작업은 Redis에 상태를 저장하지만 실행 핸들은 메모리 딕셔너리에 유지되어 프로세스 수명에 종속된다.
  Evidence: `apps/api/infrastructure/background_tasks.py`의 `_running_tasks`와 `asyncio.create_task` 사용.

- Observation: 외부 KRA API 클라이언트가 TLS 검증 비활성화(`verify=False`)를 사용한다.
  Evidence: `apps/api/infrastructure/kra_api/client.py`.

- Observation: `pip-audit`는 CVE 심각도 필드를 직접 제공하지 않아 \"critical만 차단\" 정책을 바로 코드화하기 어렵다.
  Evidence: `pip-audit --format json` 결과에 severity 필드가 없고 ID/aliases 중심으로만 제공됨.

- Observation: `/health/detailed`는 DB/Redis가 정상이더라도 background task degraded를 전체 status에 반영하지 않으면 실제 장애 신호를 놓친다.
  Evidence: Task 4 품질 리뷰에서 status 계산 로직 결함 지적 및 테스트로 재현.

- Observation: Celery eager 모드에서 `task_store_eager_result`를 설정하지 않으면 `AsyncResult` 조회 시 `pending`으로 고정되어 상태 API 검증이 불안정해진다.
  Evidence: Task 6 통합 테스트 최초 실행에서 상태가 `pending`으로 반환되며 경고 로그로 재현.

- Observation: `PostgresEnum(..., create_type=False)` 구조에서는 Postgres에서 타입 선생성 없이 `metadata.create_all`만 호출하면 실패 가능성이 있다.
  Evidence: 모델 타입 정의(`data_status`, `job_type`, `job_status`)와 기존 초기화 경로(`init_db`) 코드 검토에서 확인.

- Observation: MLflow 비활성 환경에서는 기존 구현이 run 메타데이터를 남기지 않아 재현성 추적이 누락될 수 있다.
  Evidence: `ExperimentTracker`의 비활성 경로에서 `start_run/log_*`가 no-op로 동작.

- Observation: 루트 문서가 실제 코드 구조와 불일치(`apps/collector`, `test.yml`)하여 운영 온보딩 혼선을 유발했다.
  Evidence: `README.md`의 경로/명령과 실제 워크스페이스(`apps/api`, `.github/workflows/ci.yml`) 비교 결과 확인.

## Decision Log

- Decision: 90일 계획을 “보안/관측성 기본선 → Durable Job 전환 → 실험 운영 표준화” 3단계로 나눈다.
  Rationale: 현재 최대 리스크가 인프로세스 작업 손실과 보안 기본선 미달이므로 선행 차단이 필요하다.
  Date/Author: 2026-02-21 / Codex.

- Decision: 작업 큐는 1차로 Celery + Redis를 채택하고, Temporal은 후속 확장(복잡한 보상 트랜잭션 필요 시)으로 둔다.
  Rationale: 현재 코드/인프라와의 마이그레이션 비용 대비 리스크가 가장 낮고 빠르게 가시성 있는 개선이 가능하다.
  Date/Author: 2026-02-21 / Codex.

- Decision: 실험 추적은 기존 `ExperimentTracker`를 유지하되, run 메타데이터 필수 필드를 강제하는 방식으로 확장한다.
  Rationale: 기존 코드 자산을 버리지 않고 재현성만 빠르게 강화할 수 있다.
  Date/Author: 2026-02-21 / Codex.

- Decision: Python dependency 취약점 게이트는 baseline ignore 파일(`.github/security/pip-audit-ignore.txt`) 기반의 \"신규 취약점 차단\"으로 운영한다.
  Rationale: report는 가시성 확보, gate는 신규 리스크 차단을 동시에 달성하면서 기존 알려진 취약점으로 CI가 상시 붕괴되는 것을 방지한다.
  Date/Author: 2026-02-21 / Codex.

- Decision: `/health/detailed`의 최종 status는 DB/Redis뿐 아니라 background task health를 함께 반영한다.
  Rationale: 운영 알람 기준을 서비스 실제 상태와 일치시키기 위해서다.
  Date/Author: 2026-02-21 / Codex.

- Decision: Celery 모드 테스트는 외부 worker/broker 없이 `memory:// + task_always_eager` 전략으로 CI에서 검증한다.
  Rationale: 네트워크/컨테이너 의존성을 줄여 회귀 테스트를 빠르게 유지하면서 Celery 경로를 커버할 수 있다.
  Date/Author: 2026-02-22 / Codex.

- Decision: 마이그레이션 baseline은 Alembic revision에서 Postgres enum 타입을 먼저 생성한 뒤 `Base.metadata.create_all`을 실행하는 방식으로 구성한다.
  Rationale: 기존 모델/타입 정의를 최대한 재사용하면서, 비개발 환경에서 startup `create_all` 의존을 제거하고 CI에서 `upgrade head`를 강제하기 위함이다.
  Date/Author: 2026-02-22 / Codex.

- Decision: `run_metadata`는 `commit_sha/prompt_version/data_snapshot_id/seed/mode`를 필수 키로 강제하고, 평가 결과 JSON과 MLflow(활성 시), 로컬 아티팩트(항상)에 함께 기록한다.
  Rationale: 실험 추적 백엔드 유무와 관계없이 동일한 재현성 메타데이터를 확보하기 위해서다.
  Date/Author: 2026-02-22 / Codex.

## Outcomes & Retrospective

중간 결과(2026-02-22 14:47 KST): Task 1~10 구현/문서화를 반영했다. 브랜치에는 보안/TLS 기본선, 로깅 민감정보 마스킹, Python 보안 CI 게이트, 메트릭/헬스 상태 가시화, JobRunner/Celery 전환 경로, Alembic 마이그레이션 체계, 평가/개선 루프 공통 `run_metadata` 표준화(MLflow+로컬 기록), 그리고 운영 SLO/Runbook + 문서 드리프트 정리가 포함된다. 남은 항목은 전체 회귀/부하 점검과 최종 운영 검증이다.

## Context and Orientation

이 저장소의 핵심 런타임은 `apps/api`다. 진입점은 `apps/api/main_v2.py`이며, 여기서 라우터(`routers/collection_v2.py`, `routers/jobs_v2.py`), 미들웨어(`middleware/logging.py`, `middleware/rate_limit.py`), 인프라 초기화(`infrastructure/database.py`, `infrastructure/redis_client.py`)를 연결한다.

“Durable Job”은 API 재시작, 배포, 프로세스 교체가 발생해도 작업 상태와 실행이 유실되지 않는 작업 실행 구조를 뜻한다. 현재 구현은 `infrastructure/background_tasks.py`의 인프로세스 `asyncio.create_task`를 사용하므로 이 요구를 만족하지 못한다.

“관측성(Observability)”은 추적(trace), 메트릭(metric), 로그(log)를 연계해 장애 원인을 빠르게 찾는 운영 능력이다. 현재는 구조화 로그 일부가 존재하지만, 공통 상관관계 ID와 메트릭 노출, 알림 기준(SLO)이 일관되지 않다.

“실험 재현성(Reproducibility)”은 동일 데이터와 동일 프롬프트, 동일 코드 버전으로 평가를 다시 실행했을 때 같은 결과를 재생성할 수 있는 능력이다. 현재 `packages/scripts`는 실행 자산이 분산되어 있고 run 메타데이터 표준이 약하다.

## Plan of Work

### Milestone A (1~30일): 보안과 관측성 기본선 구축

이 단계가 끝나면 운영 환경에서 위험도가 높은 보안/관측성 결함이 먼저 제거된다. 구체적으로 외부 API TLS 검증 정책이 정리되고, 민감정보 로깅이 마스킹되며, Python/Node 의존성 취약점 검사가 CI에서 강제된다. 동시에 `/metrics`와 상세 헬스체크를 통해 장애 징후를 조기에 포착할 수 있다.

### Milestone B (31~60일): Durable Job 아키텍처 전환

이 단계가 끝나면 `JobService`는 인프로세스 작업러너에 의존하지 않고 외부 워커에서 작업을 실행한다. 작업 상태는 DB/Redis에서 일관되게 조회되며 API 재시작 이후에도 작업이 지속된다. `jobs` API 계약은 유지하면서 내부 실행 계층만 교체한다.

### Milestone C (61~90일): 데이터/실험 운영 표준화와 SLO 운영

이 단계가 끝나면 프롬프트 평가와 개선 루프는 필수 run 메타데이터를 남기고, 챔피언 승격 규칙이 운영 지표와 결합된다. SLO 대시보드를 통해 API와 배치 파이프라인을 같은 운영 기준으로 모니터링한다.

## Concrete Steps

### Task 1: 외부 API 통신 보안 기본선 정리

Files:
- Modify: `apps/api/infrastructure/kra_api/client.py`
- Test: `apps/api/tests/unit/test_kra_api_service_unit.py`
- Test: `apps/api/tests/unit/test_kra_api_service_tls_policy.py` (new)

Step 1: TLS 정책 테스트를 먼저 추가한다. 기본값은 TLS 검증 ON, 명시적 개발 플래그에서만 OFF 허용을 검증한다.

Step 2: 클라이언트 생성 로직에서 `verify=False` 하드코딩을 제거하고 `settings` 기반 정책으로 치환한다.

Step 3: 실패 로그에 endpoint/attempt만 남기고 키/민감 파라미터가 출력되지 않게 확인한다.

Step 4: 단위 테스트를 실행해 RED->GREEN을 확인한다.

Step 5: 커밋한다.

### Task 2: 요청/응답 로깅 민감정보 마스킹

Files:
- Modify: `apps/api/middleware/logging.py`
- Test: `apps/api/tests/unit/test_middleware_logging.py`
- Test: `apps/api/tests/unit/test_logging_middleware_error.py`
- Test: `apps/api/tests/unit/test_logging_middleware_redaction.py` (new)

Step 1: API 키, Authorization, 토큰, 시크릿, 서비스키 패턴을 마스킹하는 테스트를 추가한다.

Step 2: 바디 로깅 경로에 키 기반 redaction 유틸을 적용한다.

Step 3: 10KB 제한과 충돌하지 않도록 성능 회귀 테스트를 추가한다.

Step 4: 관련 테스트를 실행하고 커밋한다.

### Task 3: 보안 CI 게이트 확장(Python 포함)

Files:
- Modify: `.github/workflows/ci.yml`
- Create: `.github/scripts/python_security_checks.sh`
- Modify: `apps/api/scripts/run_quality_ci.sh` (필요 시)

Step 1: `security` job에 Python dependency audit(`pip-audit`)와 정적 분석(`bandit`) 단계를 추가한다.

Step 2: 임계치 정책을 문서화한다. critical은 fail, low/medium은 보고 후 추적 이슈 생성.

Step 3: CI dry-run 또는 로컬 스크립트 실행으로 명령 정상 동작을 확인한다.

Step 4: 커밋한다.

### Task 4: 메트릭 노출과 상세 헬스체크 정합성

Files:
- Modify: `apps/api/main_v2.py`
- Modify: `apps/api/config.py`
- Create: `apps/api/monitoring/metrics.py`
- Test: `apps/api/tests/unit/test_health_detailed_branches.py`
- Test: `apps/api/tests/unit/test_metrics_endpoint.py` (new)

Step 1: `/metrics` 노출 테스트를 추가한다.

Step 2: 요청 수/지연/작업 상태 카운터를 정의하고 미들웨어 또는 라우터에서 업데이트한다.

Step 3: `/health/detailed`의 `background_tasks` 상태를 하드코딩이 아닌 실제 소스로 계산한다.

Step 4: 테스트를 실행하고 커밋한다.

### Task 5: Job 실행 추상화 계층 도입

Files:
- Create: `apps/api/infrastructure/job_runner/base.py`
- Create: `apps/api/infrastructure/job_runner/inprocess_runner.py`
- Create: `apps/api/infrastructure/job_runner/celery_runner.py`
- Modify: `apps/api/services/job_service.py`
- Test: `apps/api/tests/unit/test_job_service.py`

Step 1: `submit/get_status/cancel` 인터페이스를 정의하고 기존 구현을 `inprocess_runner`로 래핑한다.

Step 2: `JobService`가 구체 구현 대신 인터페이스를 주입받도록 바꾼다.

Step 3: 기존 테스트를 유지한 채 인터페이스 기반 테스트를 추가한다.

Step 4: 커밋한다.

### Task 6: Celery 워커 경로 구현 및 점진 전환

Files:
- Create: `apps/api/tasks/celery_app.py`
- Create: `apps/api/tasks/celery_tasks.py`
- Modify: `apps/api/config.py`
- Modify: `apps/api/main_v2.py`
- Modify: `apps/api/docker-compose.dev.yml`
- Test: `apps/api/tests/integration/test_jobs_v2_router_additional.py`
- Test: `apps/api/tests/integration/test_jobs_celery_mode.py` (new)

Step 1: 큐 브로커/백엔드 설정을 추가하고 워커 부트스트랩을 만든다.

Step 2: `JobService` 디스패치를 Celery 모드에서 실행하도록 연결한다.

Step 3: 기능 플래그(`JOB_RUNNER_MODE=inprocess|celery`)로 점진 전환을 가능하게 한다.

Step 4: 통합 테스트에서 “API 재시작 후에도 상태 조회 가능” 시나리오를 검증한다.

Step 5: 커밋한다.

### Task 7: DB 마이그레이션 체계 정비

Files:
- Create: `apps/api/alembic.ini` (또는 기존 체계 정합화)
- Create: `apps/api/alembic/` (migration env)
- Modify: `apps/api/infrastructure/database.py`
- Modify: `.github/workflows/ci.yml`

Step 1: `create_all` 중심 초기화를 비활성화하거나 개발 모드 한정으로 제한한다.

Step 2: 마이그레이션 적용 명령을 CI에 넣어 스키마 드리프트를 차단한다.

Step 3: 신규 스키마 변경 시 migration 파일 생성 규칙을 문서화한다.

Step 4: 커밋한다.

### Task 8: 프롬프트 평가 run 메타데이터 표준화

Files:
- Modify: `packages/scripts/evaluation/evaluate_prompt_v3.py`
- Modify: `packages/scripts/evaluation/mlflow_tracker.py`
- Modify: `packages/scripts/prompt_improvement/recursive_prompt_improvement_v5.py`
- Create: `packages/scripts/evaluation/run_metadata.py`
- Test: `packages/scripts/tests/test_run_metadata.py` (new)

Step 1: run 메타데이터 스키마(commit SHA, prompt version, data snapshot id, seed, mode)를 정의한다.

Step 2: 평가/개선 루프에서 동일 스키마를 강제한다.

Step 3: MLflow가 비활성 환경에서도 로컬 아티팩트에 같은 메타데이터를 남기게 만든다.

Step 4: 테스트 및 샘플 실행으로 확인 후 커밋한다.

### Task 9: SLO 정의와 운영 대시보드 연결

Files:
- Create: `docs/operations/slo.md`
- Create: `docs/operations/runbook.md`
- Modify: `apps/api/README.md`
- Modify: `README.md`

Step 1: SLI/SLO를 정의한다. 예: API availability, job completion success rate, evaluation run success rate.

Step 2: 경보 임계치와 대응(runbook)을 문서화한다.

Step 3: 운영자 온보딩 절차를 README에 반영한다.

Step 4: 커밋한다.

### Task 10: 문서-코드 드리프트 정리

Files:
- Modify: `README.md`
- Modify: `docs/project-overview.md`
- Modify: `AGENTS.md` (필요 시)

Step 1: 실제 존재하지 않는 `apps/collector` 및 구 경로 설명을 정리한다.

Step 2: 현재 실행 가능한 명령만 남기고 obsolete 명령은 archive 문서로 이동한다.

Step 3: 문서 링크 검증을 수행하고 커밋한다.

## Validation and Acceptance

모든 검증은 저장소 루트(`/Users/aiats-mbp/Developer/Personal/kra-analysis`)에서 실행한다.

1. API 회귀 테스트.

    pnpm -F @apps/api test

2. Python 직접 테스트(커버리지 포함).

    cd apps/api
    uv run pytest -q

3. 보안 게이트 검증.

    bash .github/scripts/security_checks.sh
    bash .github/scripts/python_security_checks.sh

4. 작업 내구성 시나리오 검증.

    - `JOB_RUNNER_MODE=celery`로 API/worker를 기동한다.
    - 장시간 작업을 생성한다 (`POST /api/v2/jobs`).
    - API 프로세스를 재시작한다.
    - `GET /api/v2/jobs/{job_id}`가 `queued|processing|completed|failed` 중 합리적인 상태를 유지하면 성공이다.

5. 관측성 검증.

    - `GET /health/detailed`가 DB/Redis/작업러너 상태를 실제 값으로 반환한다.
    - `GET /metrics`가 HTTP 200과 메트릭 텍스트를 반환한다.

6. 실험 재현성 검증.

    - 동일 입력으로 `evaluate_prompt_v3.py`를 두 번 실행한다.
    - 두 run 모두 동일 메타데이터 필드를 가진 아티팩트/MLflow 기록을 남기면 성공이다.

## Idempotence and Recovery

이 계획의 대부분은 멱등적으로 재실행할 수 있다. 마이그레이션은 버전 테이블 기준으로 1회 적용되며 실패 시 동일 리비전을 재실행한다. 작업러너 전환은 기능 플래그를 유지하므로 문제가 생기면 즉시 `JOB_RUNNER_MODE=inprocess`로 되돌릴 수 있다. 보안 정책 변경으로 외부 API 연결 이슈가 발생하면 “개발 전용 TLS 우회 플래그”를 임시로 활성화하되, 프로덕션 환경 변수에서는 금지한다.

## Artifacts and Notes

아래 로그/출력은 각 마일스톤 완료 시 이 섹션에 실제값으로 채운다.

- 보안 테스트 결과 요약(취약점 수, 차단 여부)
- 작업 내구성 시나리오 실행 로그(`job_id`, 상태 전이 시각)
- `/metrics` 샘플 출력 첫 20줄
- MLflow run 링크 또는 로컬 아티팩트 경로

예시 기록 형식:

    2026-03-15 Milestone A 완료
    - `pip-audit`: 0 vulnerabilities above medium
    - `/metrics`: HTTP 200, 47 lines exposed
    - `test_logging_middleware_redaction.py`: PASS

## Interfaces and Dependencies

- `apps/api/services/job_service.py`는 구체 구현을 직접 호출하지 않고 `JobRunner` 인터페이스를 의존해야 한다.

    class JobRunner(ABC):
        def submit(self, job: Job) -> str: ...
        async def status(self, task_id: str) -> dict[str, Any] | None: ...
        async def cancel(self, task_id: str) -> bool: ...

- `apps/api/config.py`에는 최소한 아래 설정이 있어야 한다.

    kra_api_verify_tls: bool
    metrics_enabled: bool
    db_auto_create_on_startup: bool
    job_runner_mode: Literal["inprocess", "celery"]
    celery_broker_url: str
    celery_result_backend: str
    celery_task_always_eager: bool
    celery_task_eager_propagates: bool
    celery_task_store_eager_result: bool

- `packages/scripts/evaluation/run_metadata.py`는 평가/개선 런타임에서 공통으로 사용할 메타데이터 생성기 함수를 제공해야 한다.

    def build_run_metadata(prompt_version: str, dataset_id: str, mode: str, seed: int = 42, ...) -> dict[str, Any]: ...

- `.github/workflows/ci.yml`의 `security` job은 Node와 Python 생태계를 모두 검사해야 하며, 실패 기준을 문서(`docs/operations/slo.md`)와 일치시켜야 한다.

---

Change note (2026-02-21 / Codex): 초기 아키텍처 리서치 결과를 반영해 90일 고도화 ExecPlan을 신규 작성했다. 구현 시작 전 기준선 문서이며, 각 Phase 완료 시 Progress/Outcomes/Artifacts를 즉시 갱신하도록 정의했다.
Change note (2026-02-22 / Codex): Task 1~5 구현 결과를 반영해 Progress/Discoveries/Decision Log/Outcomes/Interfaces를 갱신했다. Python 보안 게이트 baseline 전략과 metrics/health 상태 집계 결정을 문서에 반영했다.
Change note (2026-02-22 / Codex): Task 6 구현 결과(Celery runner/app/tasks, mode flag, dev worker compose, eager integration test)를 반영해 Progress/Discoveries/Decision Log/Outcomes/Interfaces를 갱신했다.
Change note (2026-02-22 / Codex): Task 7 구현 결과(Alembic baseline/env/ini, init_db 정책 전환, CI migration step, 운영 규칙 문서화)를 반영해 Progress/Discoveries/Decision Log/Outcomes/Interfaces를 갱신했다.
Change note (2026-02-22 / Codex): Task 8 구현 결과(run_metadata 스키마/검증/로컬 아티팩트, evaluate/improvement CLI 연결, 테스트 추가)를 반영해 Progress/Discoveries/Decision Log/Outcomes/Interfaces를 갱신했다.
Change note (2026-02-22 / Codex): Task 9~10 구현 결과(SLO/Runbook 신설, 운영 온보딩 링크 반영, 루트 README/프로젝트 개요 드리프트 정리)를 반영해 Progress/Discoveries/Outcomes를 갱신했다.

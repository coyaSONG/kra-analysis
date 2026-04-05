# 아키텍처 개선 A~I 실행 롤아웃 ExecPlan

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

`PLANS.md` is checked into this repository at `.agent/PLANS.md`. This document must be maintained in accordance with `.agent/PLANS.md`.

## Purpose / Big Picture

이 계획의 목적은 앞서 식별한 아키텍처 개선 후보 A~I를 "좋은 아이디어 목록"에서 "실제로 순서대로 구현 가능한 작업 묶음"으로 바꾸는 것이다. 이 문서가 끝까지 실행되면 `apps/api`는 하나의 job 상태 vocabulary, 하나의 schema truth, 하나의 인증 principal 표현, 하나의 KRA transport 코어를 갖게 되고, `packages/scripts`는 공통 데이터 접근 계약과 평가 런타임 계층을 공유하게 된다.

완료 후 사용자는 다음 행동으로 결과를 직접 볼 수 있어야 한다. Redis를 끈 상태에서도 `GET /health/detailed`는 HTTP 200과 `degraded`를 반환한다. `POST /api/v2/collection/async`와 `GET /api/v2/jobs/{id}`는 같은 canonical job vocabulary를 사용한다. 빈 Postgres 데이터베이스에 migration만 적용해도 앱이 기동한다. `evaluate_prompt_v3.py`는 기존 CLI 계약을 유지하면서 내부적으로 분리된 runtime 계층을 사용한다.

이 문서는 기존 후보별 설계 문서를 대체하지 않는다. 대신 실제 착수 순서, 병렬 lane, acceptance gate, rollback checkpoint를 한 곳에 묶는다. 후보별 깊은 설계는 다음 문서를 참조한다. [2026-03-19-architecture-improvement-master-plan.md](/Users/chsong/Developer/Personal/kra-analysis/docs/plans/2026-03-19-architecture-improvement-master-plan.md), [2026-03-19-architecture-remediation-execplan.md](/Users/chsong/Developer/Personal/kra-analysis/docs/plans/2026-03-19-architecture-remediation-execplan.md), [candidate-h-deep-policy-module.md](/Users/chsong/Developer/Personal/kra-analysis/plans/candidate-h-deep-policy-module.md), [2026-03-19-db-access-contract-integration-test-risk-execplan.md](/Users/chsong/Developer/Personal/kra-analysis/docs/plans/2026-03-19-db-access-contract-integration-test-risk-execplan.md), [2026-03-19-evaluate-prompt-v3-decomposition-execplan.md](/Users/chsong/Developer/Personal/kra-analysis/docs/plans/2026-03-19-evaluate-prompt-v3-decomposition-execplan.md), [2026-03-19-test-platform-fixture-strategy.md](/Users/chsong/Developer/Personal/kra-analysis/docs/superpowers/plans/2026-03-19-test-platform-fixture-strategy.md).

## Progress

- [x] (2026-03-19 23:45 KST) 50개 서브에이전트 결과를 통합해 후보 A~I의 우선순위와 의존관계를 정리했다.
- [x] (2026-03-19 23:45 KST) 후보 H, F, E, 공통 fixture 전략에 대한 개별 ExecPlan 문서가 저장소에 추가됐다.
- [x] (2026-03-19 23:58 KST) 전체 A~I를 실제 착수 순서와 acceptance gate로 재배열한 통합 롤아웃 ExecPlan 초안을 작성했다.
- [x] (2026-03-20 00:16 KST) T0 테스트 플랫폼 정비 완료. `apps/api/tests/platform/` 패키지, deterministic `FakeRedis`, `InlineTaskRunner`, `ControlledTaskRunner`, `FakeKRA`, fresh `create_app()` fixture, compatibility shimmed `tests.utils.mocks`, contract smoke test를 추가했다.
- [x] (2026-03-20 00:24 KST) T1 후보 D 런타임 경계 정리 완료. `main_v2.py`는 `create_app()`과 runtime wiring을 제공하고, `bootstrap/runtime.py`의 `AppRuntime`/`ObservabilityFacade`를 통해 `health`/`metrics`가 같은 runtime 경계를 사용한다.
- [x] (2026-03-20 01:10 KST) T2 후보 H deep policy 모듈 1차 완료. `policy/` 패키지로 authenticator/authorizer/accountant를 분리했고 `require_principal()`, `require_action()`이 principal/action/reservation을 canonical contract로 남긴다. `jobs_v2`, `collection_v2`는 `owner_ref`를 사용하고 legacy helper 재검증으로 인한 usage 이중 증가를 제거했다.
- [x] (2026-03-20 01:34 KST) T3 후보 B 상태기계 정규화 1차 완료. `services/job_contract.py`의 canonical dispatch/lifecycle enum, `job_kind_v2`/`lifecycle_state_v2` shadow field, dual-write, `running -> processing` read-compat을 도입했고 관련 jobs read/list 경계 테스트를 고정했다.
- [x] (2026-03-20 01:52 KST) T2 후보 H append-only usage accounting 완료. `usage_events` 모델과 `004_add_usage_events.sql`, `PolicyAccountingMiddleware`를 추가해 policy-guarded 요청마다 append-only usage event가 기록되도록 했다.
- [x] (2026-03-20 03:30 KST) T4 후보 I migration source of truth 고정 완료. `scripts/apply_migrations.py`는 manifest/checksum 기반으로 active migration chain만 적용하며, `infrastructure/database.py`는 non-test 환경 전체에서 manifest mismatch를 fail-closed로 거부한다.
- [x] (2026-03-20 03:18 KST) T5 후보 C KRA transport 코어 추출 완료. `infrastructure/kra_api/core.py`가 transport/retry/SSL/cache TTL/rate-limit logging 정책을 단일 코어로 제공하고 `KRAAPIService`, `KRAApiClient`가 같은 policy를 재사용한다.
- [x] (2026-03-20 03:18 KST) T6 후보 F shared DB access contract 도입 완료. `packages/scripts/shared/read_contract.py`의 `RaceKey`/`RaceSnapshot`을 중심으로 scripts가 raw row dict 대신 canonical read contract를 사용하도록 정리했다.
- [x] (2026-03-20 03:18 KST) T7 후보 G aggregate/projection adapter 도입 완료. `adapters/race_projection_adapter.py`가 `result_data`의 list/dict 혼재를 하나의 projection으로 봉합하고 `result_collection_service`, `collection_enrichment`가 같은 adapter를 통하도록 맞췄다.
- [x] (2026-03-20 02:15 KST) T8 후보 A collection orchestrator 1단계 완료. `apps/api/services/collection_workflow.py`를 추가해 batch plan 생성과 partial-failure 정책을 중앙화했고, `collection_v2.py`는 sync/async batch 모두 workflow를 통해 처리한다. `CollectionService.collect_batch_races()`는 compatibility wrapper로 workflow를 재사용한다.
- [x] (2026-03-20 03:30 KST) T9 후보 E evaluation runtime 분해 완료. `evaluate_prompt_v3.py`는 thin wrapper로 남기고 `data_loading.py`, `prediction_service.py`를 분리했으며, 평가 결과와 MLflow params에 `dataset_metadata`, `feature_schema_version`, `report_version`이 남도록 고정했다.
- [x] (2026-03-20 03:31 KST) 최종 회귀 완료. targeted API unit 76건, API integration 21건, scripts/evaluation 관련 23건, lint 검증이 모두 green이었다.
- [x] (2026-03-20 03:35 KST) full validation 완료. `apps/api` 전체 pytest는 `354 passed, 2 skipped`, coverage `81.77%`로 통과했고, `packages/scripts` 전체 pytest는 `109 passed`로 통과했다.

## Surprises & Discoveries

- Observation: 가장 안전한 시작점은 후보 A나 E가 아니라 테스트 플랫폼과 runtime 경계다.
  Evidence: auth, health, jobs, collection, rate-limit 테스트가 전역 singleton과 monkeypatch에 강하게 묶여 있어 큰 리팩터링을 바로 시작하면 회귀 탐지가 약해진다.

- Observation: 후보 B, H, I는 서로 다른 문제처럼 보이지만 모두 "canonical contract 부재"가 원인이다.
  Evidence: job vocabulary drift, ownership drift, migration baseline drift가 모두 DB/API/runtime 사이의 용어 불일치로 드러난다.

- Observation: 후보 G의 핵심 리스크는 aggregate 도입 자체보다 `result_data` shape 충돌이다.
  Evidence: 결과 수집은 top3 list를 저장하지만 enrichment는 `result_data["horses"]`를 기대한다.

- Observation: 후보 E는 `evaluate_prompt_v3.py`를 직접 해체하면 위험하고, wrapper를 먼저 고정하는 것이 안전하다.
  Evidence: CLI 계약과 산출물 계약이 여러 스크립트에 흩어져 있고, dataset skew와 feature drift 위험이 이미 높다.

- Observation: 현재 `apps/api` pytest 설정은 subset 실행에도 전체 coverage fail-under를 적용하므로, T0 단계의 작은 smoke 검증은 `--no-cov`가 필요하다.
  Evidence: `tests/platform/contracts/test_fake_redis_contract.py`와 `tests/unit/test_auth.py` subset은 test body는 통과했지만 coverage fail-under 75 때문에 실패 코드가 났다.

- Observation: `create_app()`만 추가해도 test harness에서 전역 `main_v2.app` 공유를 끊을 수 있었고, 기존 root/jobs/health smoke는 그대로 통과했다.
  Evidence: `tests/unit/test_main_v2_root.py`, `tests/integration/test_jobs_router.py`, `tests/unit/test_health_dynamic.py`가 fresh app fixture 전환 후에도 green이었다.

- Observation: jobs 경로는 owner 표현을 바꾸지 않고도 principal 타입을 먼저 도입할 수 있었다.
  Evidence: `require_principal()`이 `owner_ref == raw api key`로 principal을 정규화하고, `tests/integration/test_jobs_router.py`와 `tests/integration/test_jobs_v2_router_additional.py`가 그대로 green이었다.

- Observation: job vocabulary 정규화도 DB 스키마 변경 없이 먼저 시작할 수 있었다.
  Evidence: `services/job_contract.py`로 canonical dispatch/lifecycle enum을 분리하고도 `tests/unit/test_job_dispatch.py`, `tests/unit/test_job_service.py`, jobs integration tests가 모두 green이었다.

- Observation: 레거시 `require_resource_access()`는 같은 요청에서 API key 검증을 두 번 호출해 DB usage 카운터를 이중 증가시킬 수 있었다.
  Evidence: 기존 구현은 `require_api_key` dependency 뒤에 `verify_api_key()`를 한 번 더 호출했다. `tests/unit/test_auth_resource_access.py::test_require_resource_access_verifies_db_key_once` 추가 후에는 요청당 `today_requests`와 `total_requests`가 1만 증가한다.

- Observation: jobs read path는 DB row를 바꾸지 않고도 canonical status를 외부에 노출할 수 있었다.
  Evidence: `jobs_v2.py`와 `job_service.py`에서 `normalize_lifecycle_status()`를 적용한 뒤 `tests/integration/test_jobs_v2_router_additional.py`, `tests/integration/test_api_endpoints.py -k get_job_detail`가 green이었다.

- Observation: shadow field 도입 후에도 read cutover 없이 list filter 호환성을 먼저 확보할 수 있었다.
  Evidence: `JobService.list_jobs_with_total()`이 `lifecycle_state_v2 == normalized_status` 또는 `lifecycle_state_v2 IS NULL AND status IN (...)` 조건을 함께 사용하도록 바뀌었고, `tests/integration/test_jobs_v2_router_additional.py::test_jobs_v2_processing_filter_matches_legacy_running_row`가 green이었다.

- Observation: 새 shadow field는 service 경로뿐 아니라 async task helper도 같이 써야 null ratio가 줄어든다.
  Evidence: `tasks/async_tasks.py::_update_job_status()`에 dual-write를 넣은 뒤 `tests/unit/test_async_tasks.py`에서 success/fail/batch/full-pipeline job row의 `lifecycle_state_v2`가 모두 기대값으로 채워졌다.

- Observation: policy reservation만으로는 회계 분리가 끝나지 않았고, app-level finalize 지점이 필요했다.
  Evidence: `require_action()`은 dependency 안에서 reservation만 만들 수 있었고 response status/outcome을 알 수 없었다. `PolicyAccountingMiddleware`를 추가한 뒤 `tests/integration/test_policy_accounting.py`에서 `jobs.list`/`jobs.read` 요청마다 `usage_events` row가 1개씩 기록됐다.

- Observation: migration runner가 현재 unified schema와 다른 legacy verifier를 기준으로 보고 있었다.
  Evidence: 기존 `apply_migrations.py`는 `race_results`, `collection_jobs`, `prompt_versions` 같은 비활성 테이블을 필수로 검증했다. checksum-backed `schema_migrations` bookkeeping과 현재 테이블 목록으로 바꾼 뒤, startup preflight helper도 마지막 migration head를 기준으로 비교하도록 정리했다.

- Observation: collection workflow는 route와 service 사이의 batch policy를 한곳으로 모을 수 있었다.
  Evidence: `apps/api/services/collection_workflow.py`가 batch plan, partial-failure accumulation, async job submission을 담당하고, `collection_v2.py`와 `CollectionService.collect_batch_races()`는 그 workflow를 호출한다. `tests/integration/test_collection_workflow_router.py`가 delegation을 고정한다.

## Decision Log

- Decision: 실제 구현 순서는 `D/H/B/I -> C/F/G -> A/E`로 고정한다.
  Rationale: runtime, principal, state, schema truth가 먼저 잠겨야 이후의 deep module이 재작업 없이 올라간다.
  Date/Author: 2026-03-19 / Codex.

- Decision: 공통 fixture 전략을 별도 선행 작업 T0로 승격한다.
  Rationale: 큰 리팩터링일수록 경계 테스트의 결정성이 우선이며, 현재 저장소는 그 기반이 약하다.
  Date/Author: 2026-03-19 / Codex.

- Decision: 후보 B의 상태기계 통합과 vocabulary 통합은 같은 티켓으로 처리하지 않는다.
  Rationale: 상태와 어휘를 동시에 바꾸면 rollback과 mismatch 진단이 어려워진다.
  Date/Author: 2026-03-19 / Codex.

- Decision: 후보 G는 aggregate write 이전에 adapter로 `result_data` shape를 봉합한다.
  Rationale: 현재 충돌이 가장 즉각적인 도메인 버그이며, 이를 고정하지 않으면 dual-write 비교가 불가능하다.
  Date/Author: 2026-03-19 / Codex.

- Decision: 후보 E는 `PromptEvaluatorV3` 호환 래퍼를 마지막까지 유지한다.
  Rationale: 평가 스크립트는 소비자가 많고, CLI 호환성은 연구 생산성에 직접 영향을 준다.
  Date/Author: 2026-03-19 / Codex.

- Decision: T0에서는 real Redis fallback을 유지하지 않고 deterministic `FakeRedis`를 기본 fixture로 즉시 교체한다.
  Rationale: 현재 테스트 플랫폼의 가장 큰 문제는 로컬 Redis 유무에 따라 동작이 달라지는 비결정성이며, `FakeRedis`가 cache/rate-limit/API key limiter surface를 충분히 흉내낼 수 있다.
  Date/Author: 2026-03-20 / Codex.

## Outcomes & Retrospective

현재는 T0를 착수한 상태다. 첫 구현 결과로 `tests/platform/` 패키지가 추가됐고, Redis 관련 테스트는 더 이상 real Redis 존재 여부에 의존하지 않아도 된다. 아직 fake runner, fake auth harness, fresh app factory는 남아 있으므로 T0는 완료가 아니다. 완료 시 이 섹션에는 각 티켓의 실제 결과, rollout 중 발생한 contract drift, 남은 shim, 삭제 가능한 legacy 경로를 기록한다. 특히 최종 상태에서 무엇이 canonical truth가 되었는지 명시적으로 남겨야 한다.

## Context and Orientation

이 저장소의 활성 런타임은 `apps/api/main_v2.py`다. 여기서 라우터, middleware, database, Redis, background task runner가 연결된다. `apps/api/services`는 수집과 jobs 같은 업무 규칙을 담고, `packages/scripts`는 평가, ML, autoresearch 같은 오프라인 소비자를 담는다.

"deep module"은 외부에는 작은 인터페이스만 보이고 내부에서 복잡한 규칙을 숨기는 모듈이다. 이 저장소에서 목표하는 deep module은 `RaceCollectionWorkflow`, `JobCoordinator`, `KRAGateway`, `AppRuntime`, `AuthenticatedPrincipal` 같은 것들이다. 반대로 현재 문제는 얕은 wrapper와 전역 state가 많아 복잡성이 밖으로 새어 나온다는 점이다.

"shadow field"는 기존 필드를 바로 바꾸지 않고 새 canonical 값을 같은 row에 함께 기록하는 additive migration 기법이다. 후보 B와 G에서 중요하다. "dual-write"는 legacy와 canonical을 동시에 쓰는 단계이고, "cutover"는 읽기 우선순위를 canonical로 바꾸는 단계다. "fail-open"은 의존성 장애가 있어도 핵심 요청을 막지 않고 degraded 상태로 계속 처리하는 정책이다. Redis 관련 health/rate-limit과 KRA optional API fan-out이 여기에 해당한다.

## Plan of Work

이 작업은 다섯 개 lane으로 진행한다. 첫 lane은 테스트/런타임 기준선이다. 여기서는 T0과 T1을 수행해 fresh app factory, runtime facade, deterministic fake를 먼저 만든다. 둘째 lane은 identity와 state 기준선이다. 여기서는 T2와 T3을 수행해 principal과 job lifecycle의 canonical 용어를 고정한다. 셋째 lane은 persistence truth다. 여기서는 T4와 T6을 수행해 migration-only bootstrap과 shared read contract를 세운다. 넷째 lane은 ingress/aggregate 정리다. 여기서는 T5와 T7을 수행해 KRA transport 코어와 Race aggregate adapter를 만든다. 다섯째 lane은 큰 업무 흐름 정리다. 여기서는 T8과 T9를 수행해 collection orchestrator와 evaluation runtime decomposition을 완성한다.

T0에서는 [2026-03-19-test-platform-fixture-strategy.md](/Users/chsong/Developer/Personal/kra-analysis/docs/superpowers/plans/2026-03-19-test-platform-fixture-strategy.md)를 기준으로 `apps/api/tests/conftest.py`와 scripts 테스트 fixture를 정리한다. `FakeRedis`, `FakeKRA`, `InlineTaskRunner`, `ControlledTaskRunner`, `env-key`와 `db-key`를 분리한 auth fixture, fresh app fixture를 추가하고 기존 global singleton mutation 테스트를 줄인다.

T1에서는 후보 D를 착수한다. `apps/api/main_v2.py`, `apps/api/config.py`, `apps/api/routers/health.py`, `apps/api/routers/metrics.py`, `apps/api/middleware/logging.py`, `apps/api/middleware/rate_limit.py`를 중심으로 runtime kernel을 만든다. 공개 목표는 `create_app()` 또는 동등한 fresh runtime 진입점, `AppRuntime`, `ObservabilityFacade`다. 이 단계에서 `/health`, `/health/detailed`, `/metrics`, request logging, rate-limit의 실제 wiring과 테스트 wiring을 일치시킨다.

T2에서는 후보 H를 실행한다. [candidate-h-deep-policy-module.md](/Users/chsong/Developer/Personal/kra-analysis/plans/candidate-h-deep-policy-module.md)를 기준으로 `AuthenticatedPrincipal`, `PrincipalAuthenticator`, `PolicyAuthorizer`, `UsageAccountant`를 추가하고 `dependencies/auth.py`는 legacy wrapper로 남긴다. jobs 경로는 새 principal을 사용하되 외부 404/401/429 계약은 유지한다.

T3에서는 후보 B를 1단계만 수행한다. `lifecycle_state_v2`, `job_kind_v2`, 필요 시 `job_family_v2`를 도입하고 `JobStatus`, `SubmissionStatus`, `DispatchAction`을 분리한다. 이 단계에서는 상태 정규화와 dual-write만 하고, API의 기본 응답 shape는 유지한다.

T4에서는 후보 I를 수행한다. `apps/api/scripts/apply_migrations.py`를 manifest/checksum/advisory lock 기반 runner로 바꾸고, `apps/api/infrastructure/database.py`는 non-test에서 `create_all()`을 금지한다. mixed schema 감지는 fail-closed로 설계한다.

T5에서는 후보 C를 진행한다. `apps/api/services/kra_api_service.py`와 `apps/api/infrastructure/kra_api/client.py`의 transport/retry/SSL/cache policy를 하나의 core로 수렴시킨다. `KRAResponseAdapter`는 envelope decode와 endpoint decode로 역할을 나누고, raw payload sidecar와 golden fixture를 유지한다.

T6에서는 후보 F를 진행한다. [2026-03-19-db-access-contract-integration-test-risk-execplan.md](/Users/chsong/Developer/Personal/kra-analysis/docs/plans/2026-03-19-db-access-contract-integration-test-risk-execplan.md)를 기준으로 shared `RaceKey`, `RaceSnapshot`, `RaceSummary`, read repository contract를 만든다. scripts는 sync 구현체를 통해 같은 read contract를 사용하고, direct Supabase path는 shadow adapter 또는 legacy boundary로 격리한다.

T7에서는 후보 G를 진행한다. aggregate 자체를 바로 정본으로 바꾸지 말고 `LegacyResultAdapter`와 `RaceCompatibilityAdapter`로 현재 `result_data` shape 충돌을 먼저 봉합한다. 그 뒤 `RaceAggregate`, `RaceProjector`, `aggregate_data` 또는 동등한 저장 구조를 additive로 도입한다.

T8에서는 후보 A를 진행한다. `CollectionService`를 직접 해체하기보다 `RaceCollectionWorkflow` 또는 `CollectionOrchestrator`를 앞단에 두고 sync/async/batch/full-pipeline을 모두 같은 공개 인터페이스로 수렴시킨다. optional API fail-open과 partial-failure policy는 workflow 내부 정책으로 숨긴다.

T9에서는 후보 E를 진행한다. [2026-03-19-evaluate-prompt-v3-decomposition-execplan.md](/Users/chsong/Developer/Personal/kra-analysis/docs/plans/2026-03-19-evaluate-prompt-v3-decomposition-execplan.md)를 기준으로 `PromptEvaluatorV3`를 thin wrapper로 고정하고 `DataLayer`, `PredictionService`, `MetricsAggregator`, `ReportBuilder`를 순서대로 추출한다. dataset metadata와 feature schema version을 산출물에 강제한다.

## Concrete Steps

모든 명령은 저장소 루트 `/Users/chsong/Developer/Personal/kra-analysis`에서 실행한다.

1. 선행 문서와 기준선 확인.

    sed -n '1,220p' .agent/PLANS.md
    sed -n '1,260p' docs/plans/2026-03-19-architecture-rollout-execplan.md
    sed -n '1,260p' docs/superpowers/plans/2026-03-19-test-platform-fixture-strategy.md

2. T0 완료 검증용 테스트 스코프 확인.

    cd apps/api
    uv run pytest -q tests -k "health or metrics or auth or jobs or rate_limit"

   기대 결과는 현재 boundary가 약한 영역을 baseline으로 확보하는 것이다. 이 단계에서 실패가 있어도 된다. 중요한 것은 이후 acceptance와 비교할 기준을 남기는 것이다.

3. T1 완료 검증.

    cd apps/api
    uv run pytest -q tests/unit/test_main_v2_root.py tests/unit/test_metrics.py tests/unit/test_health_dynamic.py
    uv run uvicorn main_v2:app --reload

   기대 결과는 `/health`, `/health/detailed`, `/metrics`가 모두 응답하고 Redis 미가용 시에도 앱이 기동하는 것이다.

4. T2와 T3 완료 검증.

    cd apps/api
    uv run pytest -q tests -k "auth or jobs_v2 or job_service or job_dispatch or async_tasks"

   기대 결과는 owner/non-owner, over-limit, submit/get/cancel, batch alias compatibility가 모두 green인 것이다.

5. T4 완료 검증.

    cd apps/api
    uv run python scripts/apply_migrations.py --help
    uv run pytest -q tests -k "migration or database"

   기대 결과는 빈 데이터베이스 부트스트랩 경로가 migration-only로 설명되고, mixed state는 fail-closed로 거부되는 것이다.

6. T5, T6, T7 완료 검증.

    cd apps/api
    uv run pytest -q tests -k "kra or collection or result_collection or field_mapping"
    cd ../../packages/scripts
    uv run pytest -q tests

   기대 결과는 KRA golden fixture, aggregate/result adapter, shared read contract 관련 테스트가 green인 것이다.

7. T8, T9 완료 검증.

    cd /Users/chsong/Developer/Personal/kra-analysis
    pnpm -F @apps/api test
    cd packages/scripts
    uv run pytest -q

   기대 결과는 API와 scripts 양쪽이 같은 canonical contract를 소비하면서 기존 CLI/HTTP 계약을 유지하는 것이다.

## Validation and Acceptance

T0 acceptance는 새 fake와 fixture를 두 개 이상의 영역이 실제로 공유하는 것이다. 예를 들어 jobs와 health가 같은 `FakeRedis`를 쓰고, collection과 result collection이 같은 `FakeKRA`를 사용해야 한다.

T1 acceptance는 다음 행동으로 본다. 앱을 띄운 뒤 `GET /health`는 항상 200, `GET /health/detailed`는 Redis 장애 시에도 200과 `degraded`, `GET /metrics`는 `kra_requests_total`, `kra_database_up`, `kra_background_tasks_active`를 포함한다. request logging은 실제 등록된 middleware 기준으로 검증되어야 한다.

T2 acceptance는 유효한 API key로 jobs를 생성/조회할 수 있고, non-owner는 여전히 404를 받으며, 한 요청당 usage accounting이 한 번만 증가하는 것이다.

T3 acceptance는 새로 생성되는 job row의 `*_v2` 필드 null 비율이 0이고, `processing`과 `running` 같은 legacy alias가 read-compat만 유지되는 것이다.

T4 acceptance는 빈 DB에서 canonical migration chain만으로 앱을 기동할 수 있고, non-test startup이 migration head 없이 조용히 schema를 생성하지 않는 것이다.

T5 acceptance는 active KRA 경로가 하나의 transport/retry matrix를 사용하고, raw payload -> normalized record golden fixture parity가 유지되는 것이다.

T6 acceptance는 scripts가 ORM을 직접 import하지 않고 shared read contract만 통해 데이터를 읽는 것이다.

T7 acceptance는 `result_data`가 list든 dict든 adapter를 통해 동일한 도메인 결과로 읽히고, aggregate/projection dual-write가 가능해지는 것이다.

T8 acceptance는 sync/async/full-pipeline이 같은 public workflow 인터페이스를 통하고, partial-failure policy가 한곳에만 정의되는 것이다.

T9 acceptance는 `evaluate_prompt_v3.py` CLI 계약이 유지되고, dataset metadata, feature schema version, report version이 결과물과 MLflow artifact에 기록되는 것이다.

## Idempotence and Recovery

모든 작업은 additive하게 진행한다. 각 티켓은 "새 경로 추가 -> dual-write 또는 shadow -> cutover -> cleanup" 순서를 따른다. destructive schema 변경, legacy field drop, shim 제거는 항상 마지막 wave로 미룬다.

Rollback 우선순위는 코드 revert보다 flag revert다. 예를 들어 후보 B는 `lifecycle_state_v2` read를 끄고 legacy read로 되돌릴 수 있어야 하고, 후보 G는 `RACE_READ_MODEL=legacy`로 즉시 복귀할 수 있어야 한다. 후보 C는 `FF_KRA_ADAPTER_V2`를 끄면 기존 adapter path로 돌아가야 한다. 후보 E는 `PromptEvaluatorV3` thin wrapper가 마지막까지 존재하므로 새 runtime 모듈을 우회할 수 있어야 한다.

Mixed schema, unknown job kind, ownership mismatch, report validator failure, health 500, collection partial-failure 급증이 관찰되면 다음 티켓으로 진행하지 말고 현재 티켓 안에서 원인을 정리한 뒤 이 문서의 `Progress`와 `Surprises & Discoveries`를 갱신한다.

## Artifacts and Notes

핵심 티켓 맵은 다음과 같다.

    T0: Test Platform / Fixtures
    T1: D Runtime Kernel
    T2: H Deep Policy Module
    T3: B Job Lifecycle Shadow Cutover
    T4: I Migration Truth
    T5: C KRA Transport Core
    T6: F Shared DB Read Contract
    T7: G Race Aggregate Adapter
    T8: A Collection Orchestrator
    T9: E Evaluation Runtime Decomposition

병렬 lane은 다음과 같다.

    Lane 1: T0 -> T1
    Lane 2: T2 -> T3
    Lane 3: T4 -> T6
    Lane 4: T5 -> T7
    Lane 5: T8 -> T9

실제 크리티컬 패스는 `T0 -> T1 -> T2 -> T3 -> T4 -> T5/T6/T7 -> T8 -> T9`다. T5, T6, T7은 일부 병렬화가 가능하지만 acceptance는 T4 이후부터 의미가 있다.

## Interfaces and Dependencies

이 계획이 완료될 때 최소한 다음 인터페이스가 존재해야 한다.

`apps/api/main_v2.py` 또는 동등한 bootstrap 경로에는 `create_app(...) -> FastAPI`와 `get_runtime() -> AppRuntime`이 있어야 한다. `AppRuntime`은 settings, resource registry, observability facade를 소유해야 한다.

`apps/api/dependencies/auth.py` 뒤에는 `AuthenticatedPrincipal`, `PrincipalAuthenticator`, `PolicyAuthorizer`, `UsageAccountant`가 존재해야 한다. 외부 라우터는 `require_principal()`과 `require_action(...)` 또는 동등한 얇은 dependency만 알아야 한다.

`apps/api/services/job_service.py` 앞에는 `JobCoordinator` 또는 동등한 facade가 존재해야 한다. 이 facade는 `submit`, `snapshot`, `cancel`을 공개하고 내부적으로 `DispatchAction`, `JobStatus`, state store, runner를 조합해야 한다.

`apps/api/services/kra_api_service.py`와 `apps/api/infrastructure/kra_api/client.py` 사이에는 하나의 transport core가 존재해야 한다. 이 코어는 SSL verify, timeout, retry matrix, cache policy를 authoritative하게 관리해야 한다.

`packages/scripts`와 `apps/api`는 공통으로 `RaceKey`, `RaceSnapshot`, `RaceSummary` 또는 동등한 read contract를 공유해야 한다. ORM session이나 psycopg2 connection을 공유하면 안 된다.

`apps/api/services/collection_service.py` 앞에는 `RaceCollectionWorkflow` 또는 `CollectionOrchestrator`가 존재해야 한다. 이 인터페이스는 최소한 `collect_race(...)`와 `collect_batch(...)`를 제공해야 한다.

`packages/scripts/evaluation/evaluate_prompt_v3.py`는 thin wrapper로 남아 있어야 하며 내부적으로 `DataLayer`, `PredictionService`, `MetricsAggregator`, `ReportBuilder` 또는 동등한 분리된 계층을 호출해야 한다.

Change note: 2026-03-19에 50개 서브에이전트 결과와 후보별 개별 ExecPlan을 바탕으로, 전체 A~I를 실제 착수 가능한 티켓과 lane으로 재배열한 통합 롤아웃 문서를 추가했다. 이유는 기존 문서들이 후보별 깊이는 충분했지만, 실제 실행 순서와 acceptance gate가 여러 파일에 분산돼 있었기 때문이다.

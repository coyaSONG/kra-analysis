# 아키텍처 리팩터링 후 레거시 맵

**Date:** 2026-03-21
**Category:** discovery
**Status:** active
**Related files:** apps/api/services/, apps/api/routers/, apps/api/infrastructure/, packages/scripts/evaluation/

## Context

2026-03-19~21 사이 아키텍처 개선 A~I가 순차적으로 실행되었다 (커밋 `8d55517`~`7e3c3b6`). 이 과정에서 새로운 모듈들이 도입되면서 기존 코드의 일부가 레거시가 되었다. 실행 계획은 `docs/plans/2026-03-19-architecture-rollout-execplan.md`에 기록되어 있다.

## 2026-03-21 레거시 정리 완료

아래 항목들은 의존성 분석을 통해 활성 코드에서 참조가 없음을 확인한 뒤 삭제되었다.

### 삭제된 파일 (Tier 1 — import chain 완전히 끊김)

| 파일 | 이유 |
|------|------|
| `apps/api/services/collection_workflow.py` | facade로 대체됨. 테스트 1곳만 import |
| `apps/api/tests/unit/test_collection_workflow.py` | 위 파일 전용 테스트 |
| `apps/api/routers/race.py` | `main_v2.py`에 mount되지 않음 (v1 레거시) |
| `apps/api/services/race_service.py` | unmounted router의 서비스 |
| `apps/api/tests/unit/test_race_router_supabase_guard.py` | 삭제된 race router 전용 테스트 |
| `packages/scripts/evaluation/evaluate_prompt_v3_base.py` | import 없는 v3 standalone 복제본 |
| `packages/scripts/hybrid_predictor.py` | import 없음 |
| `packages/scripts/data_analysis/` (전체) | import 없음 |
| `packages/scripts/archive/` (전체) | 폐기된 실험 파일들 |

### 삭제된 파일 (Tier 2 — Tier 1 삭제 후 고아)

| 파일 | 이유 |
|------|------|
| `apps/api/infrastructure/kra_api/client.py` | `race_service.py` 삭제 후 활성 사용처 없음. retry/SSL 테스트는 `core.py` 테스트로 대체 |
| `apps/api/tests/unit/test_kra_api_client_retry.py` | 삭제된 `client.py` 전용. `test_kra_api_core.py`에 동등 테스트 존재 |
| `apps/api/tests/unit/test_kra_api_client_ssl.py` | Settings 검증 테스트 1개를 `test_kra_api_core.py`로 이동 후 삭제 |
| `apps/api/tests/test_data_validation.py` | 삭제된 `KRAApiClient` 사용하는 standalone 검증 스크립트 |
| `apps/api/tests/test_nodejs_comparison.py` | 삭제된 Node.js 스크립트와 v1 API 비교 (레거시) |
| `packages/scripts/ml/` (전체) | `hybrid_predictor.py`만 사용했으며 해당 파일도 삭제됨 |
| `packages/scripts/batch_collect_2025.py` | standalone script, import 없음 |

### 삭제된 패키지 (Tier 4 — Phantom packages)

| 대상 | 이유 |
|------|------|
| `packages/shared-types/` (전체) | workspace 내 소비자 0. Python 중심 프로젝트에서 미사용 TS 타입 |
| `packages/typescript-config/python.json` | 어떤 tsconfig도 extend하지 않음 |
| `package.json`의 `quality:node:*` 스크립트 | `shared-types` 삭제에 따라 제거 |

### 테스트 마이그레이션

- `test_kra_api_client_ssl.py`의 `test_settings_disallow_disabling_kra_ssl_outside_development` → `test_kra_api_core.py`로 이동 (Settings 검증이므로 보존)

## Finding: 아직 남아있는 레거시 코드

### 1. `apps/api/services/kra_api_service.py` — 축소된 서비스 (활성)

- **현재 상태**: transport/retry/SSL/cache 로직이 `infrastructure/kra_api/core.py`로 추출됨. thin wrapper 역할이지만 **21곳에서 import**되어 삭제 불가
- **향후**: 점진적으로 `core.py` 직접 사용으로 전환 가능

### 2. `packages/scripts/shared/data_adapter.py` — 부분 레거시 (활성)

- **현재 상태**: `convert_basic_data_to_enriched_format()`이 5곳에서 활발히 사용 중
- **향후**: `data_loading.py`로 통합하거나 `read_contract.py` 기반으로 전환

### 3. `apps/api/services/collection_service.py` — `collect_batch_races()` 메서드

- **현재 상태**: 테스트 3곳에서만 호출. 활성 라우터 경로에서 미사용
- **향후**: 테스트를 facade 경유로 변경 후 메서드 제거

### 4. `packages/scripts/evaluation/evaluate_prompt_v3.py` — 의도된 thin wrapper

- 핵심 로직이 `data_loading.py`, `prediction_service.py`, `report_schema.py`로 분리됨
- CLI 진입점으로서 의도적으로 유지

### 5. Job vocabulary 레거시

- `job_kind_v2` / `lifecycle_state_v2` shadow field dual-write 중. read cutover 대기

### 6. Migration verifier 레거시

- checksum-backed `schema_migrations`로 전환 완료. 정상 운영 중

## Impact

향후 작업 시 고려사항:
1. **collection 관련 변경** → `kra_collection_module.py` facade를 통해 작업
2. **KRA API 호출 변경** → `infrastructure/kra_api/core.py`가 transport 정책의 single source of truth
3. **평가 스크립트 변경** → `data_loading.py`, `prediction_service.py`를 사용. `evaluate_prompt_v3.py`는 thin wrapper로만 유지
4. **Job 상태 관련** → `job_contract.py`의 canonical enum 사용. old `status` 필드는 아직 read에 사용되지만 향후 cutover 예정
5. **인증/인가** → `require_principal()` + `require_action()` 사용

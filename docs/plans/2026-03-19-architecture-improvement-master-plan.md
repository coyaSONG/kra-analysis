# 아키텍처 개선 마스터 플랜

## 목적

서브에이전트 병렬 분석 결과를 바탕으로 `apps/api`와 `packages/scripts`의 핵심 아키텍처 개선 후보 A~I에 대한 설계, 점진적 마이그레이션, 테스트 전환, 리스크 대응 방향을 정리한다.

## 후보

### A. Race Collection Workflow
- `CollectionService`의 수집/전처리/보강/결과/배치를 `RaceCollectionWorkflow` 또는 `CollectionOrchestrator`로 재구성

### B. Job Lifecycle Coordinator
- `create/start/status/cancel` 분산 상태기계를 `submit/snapshot/cancel` 중심의 단일 coordinator로 재구성

### C. KRA Gateway / Record Decoder
- `kra_api_service.py`, `infrastructure/kra_api/client.py`, `kra_response_adapter.py`, `field_mapping.py`를 하나의 게이트웨이 코어로 수렴

### D. Operational Runtime / 설정값 산재
- health/metrics/logging/rate-limit/settings 경계를 통합하고 운영 상태 스냅샷을 일관화

### E. 평가 파이프라인 중복
- `evaluate_prompt_v3.py`를 `Data Layer`, `Prediction Service`, `Metrics Aggregator`, `Report Builder` 또는 포트 기반 engine으로 분해

### F. DB 접근 패턴 이원화
- async SQLAlchemy와 sync psycopg2 사이의 공유 데이터 접근 계약 도입

### G. Race Aggregate / Projection
- `Race` 관련 DTO/ORM/JSON blob을 관통하는 canonical aggregate/projection 수립

### H. AccessPolicy
- 인증, 권한, 사용량 회계, ownership 판정을 분리된 정책 모듈로 재구성

### I. Schema Bootstrapper / Migration Verifier
- `create_all()`과 migration 스크립트 충돌을 제거하고 migration-only bootstrap 기준 확립

## 공통 원칙

- 공개 API 계약과 DTO는 초기 단계에서 유지한다.
- 내부에 새로운 deep module을 먼저 추가하고, 기존 경로는 adapter로 유지한다.
- 삭제와 이름 변경은 마지막 단계로 미룬다.
- additive migration만 허용하고 destructive schema 변경은 최종 정리 단계로 미룬다.
- 테스트는 내부 helper 단위에서 boundary/contract 중심으로 이동한다.

## 페이즈

### Phase 1
- D: health/metrics/logging/rate-limit 정합성 복구
- B: jobs API와 runner vocabulary 정렬의 첫 단계
- H: 인증/ownership 계약 정직성 복구
- 문서/README 기준선 정리

### Phase 2
- I: unified migration baseline 확정
- B: runner/state store/catalog 경계 도입
- C: KRA gateway 공통 코어 추출
- F: 공통 데이터 접근 계약 초안 도입

### Phase 3
- A: collection orchestrator 도입 후 sync/async/pipeline 경로 수렴
- G: Race aggregate/projection 도입
- E: evaluation engine 분해
- 운영 acceptance, runbook, SLO 연결

## 산출물

- 후보 A~I별 인터페이스 설계안
- 단계별 마이그레이션 계획
- 테스트 전환 계획
- 리스크 및 완화 전략
- Phase 1/2/3 실행 로드맵

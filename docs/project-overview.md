# 프로젝트 개요

## 목표

KRA 경마 데이터를 기반으로, 수집/보강/평가 파이프라인을 API와 스크립트로 운영하는 예측 시스템입니다.

핵심 목표는 다음 3가지입니다.

1. 경주 전 데이터 수집 및 정규화
2. 비동기 작업 기반 안정적 처리(내구성 있는 작업 실행)
3. 평가/개선 루프의 재현성 확보(`run_metadata` 표준화)

## 현재 아키텍처

### 런타임 구성

1. `apps/api`
- FastAPI 엔드포인트 제공
- `/api/v2/collection`, `/api/v2/jobs` 네임스페이스 운영
- DB/Redis 연동, 상세 헬스체크 및 메트릭 노출
- 작업 러너 모드: `inprocess` 또는 `celery`

2. `packages/scripts`
- 프롬프트 평가: `evaluation/evaluate_prompt_v3.py`
- 재귀 개선: `prompt_improvement/recursive_prompt_improvement_v5.py`
- 평가/개선 공통 run metadata 기록

### 데이터 흐름

1. 수집 요청 수신 (`/api/v2/collection`)
2. Job 생성/큐잉 (`/api/v2/jobs`)
3. 작업 실행 (inprocess 또는 celery worker)
4. 상태/결과 저장 (DB + 필요 시 Redis 상태)
5. 평가 스크립트 실행 후 결과 + `run_metadata` 저장

## 운영 기준

- 신뢰성 기준: `operations/slo.md`
- 장애 대응 절차: `operations/runbook.md`
- API 상세 사용법: `../apps/api/README.md`

## 성공 지표

1. API Availability (30일) `>= 99.5%`
2. Job Completion Success Rate (7일) `>= 98%`
3. Evaluation Run Success Rate (7일) `>= 95%`
4. 재현성: 평가 결과에 공통 `run_metadata` 필수 필드 100% 기록

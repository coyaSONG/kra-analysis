# SLO / SLI 정의

## 문서 목적

이 문서는 API 런타임, 비동기 작업 처리, 평가 파이프라인의 운영 신뢰성 목표(SLO)를 정의합니다.

- 적용 범위: `apps/api`, `packages/scripts` 운영 실행
- 기준 시간대: KST
- 기본 측정 윈도우: 30일 롤링

## 서비스 계층

1. API 계층: FastAPI 엔드포인트 응답
2. Job 계층: `/api/v2/jobs`로 시작된 비동기 작업의 완료 품질
3. Evaluation 계층: `evaluate_prompt_v3.py`/`recursive_prompt_improvement_v5.py` 실행 성공률

## SLI/SLO

### 1) API Availability

- SLI: 정상 응답 비율 = `1 - (5xx 응답 수 / 전체 요청 수)`
- SLO: 30일 기준 `>= 99.5%`
- 데이터 소스:
  - Prometheus endpoint: `/metrics`
  - 메트릭: `kra_http_requests_total{status="5xx"}` / `kra_http_requests_total`
- 에러 버짓: 0.5% (30일)

### 2) API Latency (p95)

- SLI: 읽기 엔드포인트 p95 지연
- SLO:
  - `GET /health`, `GET /health/detailed`, `GET /api/v2/jobs/*`: p95 `<= 1.5s`
- 데이터 소스:
  - `/metrics`의 `kra_http_request_duration_seconds_*`
  - 필요 시 로그 기반 percentile 집계 병행

### 3) Job Completion Success Rate

- SLI: 종료 상태 작업 중 성공 비율
- 정의:
  - 분모: `status in (completed, failed, cancelled)`
  - 분자: `status = completed`
- SLO: 7일 롤링 `>= 98.0%`
- 데이터 소스:
  - `jobs` 테이블 집계
  - `/api/v2/jobs` 조회 결과

예시 SQL:

```sql
SELECT
  100.0 * SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END)
    / NULLIF(SUM(CASE WHEN status IN ('completed', 'failed', 'cancelled') THEN 1 ELSE 0 END), 0)
    AS success_rate_pct
FROM jobs
WHERE created_at >= NOW() - INTERVAL '7 day';
```

### 4) Evaluation Run Success Rate

- SLI: 평가 실행 성공 비율
- 정의:
  - 분모: 평가 실행 건수
  - 분자: 결과 JSON 생성 + `run_metadata` 검증 통과 건수
- SLO: 7일 롤링 `>= 95.0%`
- 데이터 소스:
  - `packages/scripts` 결과 산출물
  - MLflow run(사용 시)

## Alert 임계치

### P1 (즉시 대응)

- API Availability 5분 평균 `< 99.0%`
- `/health/detailed`에서 `database=unhealthy` 3회 연속
- Job Success Rate 1시간 `< 90%`

### P2 (업무시간 내 대응)

- API Availability 15분 평균 `< 99.5%`
- API Latency p95 15분 `> 2.0s`
- Job Success Rate 24시간 `< 98%`
- Evaluation Success Rate 24시간 `< 95%`

## 대시보드 권장 패널

1. API request rate / 5xx ratio
2. API p95 latency (핵심 read endpoints)
3. Job status 분포 (`pending`, `queued`, `processing`, `completed`, `failed`, `cancelled`)
4. Runner health (`/health/detailed.background_tasks`)
5. Evaluation success/failure count (일 단위)

## 운영 규칙

- SLO 위반 시 `runbook.md` 절차를 따른다.
- SLO/SLA 변경은 PR로 제안하고, 변경 전후 2주 지표를 첨부한다.
- 신규 엔드포인트/작업 유형 추가 시 해당 SLI 반영 여부를 같은 PR에서 검토한다.

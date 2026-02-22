# 운영 Runbook

## 목적

SLO 위반 또는 주요 장애 발생 시, 동일한 절차로 진단/복구/커뮤니케이션을 수행하기 위한 운영 가이드입니다.

## 공통 초기 점검

1. 현재 장애 범위 확인
- `/health`
- `/health/detailed`
- `/metrics`

2. 최근 배포/설정 변경 확인
- `JOB_RUNNER_MODE`
- `DATABASE_URL`, `REDIS_URL`
- Alembic migration 적용 여부

3. 로그 확인
- API: 구조화 로그의 `error_id`, `path`, `method`
- Worker(Celery 모드): worker stderr/stdout

## 시나리오별 대응

### A. API Availability 저하 (5xx 급증)

증상:
- 5분 기준 실패율 급증
- `/health` 또는 핵심 엔드포인트 오류

조치:
1. `/health/detailed`에서 `database`, `redis`, `background_tasks` 상태 확인
2. DB 연결 실패 시:
- DB endpoint/credential 점검
- `uv run alembic current`로 migration mismatch 확인
3. Redis 실패 시:
- Redis 프로세스/네트워크 점검
- Celery 모드면 broker/backend 연결 재확인
4. 즉시 완화가 필요하면:
- 트래픽 제한
- 마지막 안정 버전으로 롤백

### B. Job Success Rate 저하

증상:
- `failed`, `cancelled` 비율 상승
- 작업 지연 및 재시도 증가

조치:
1. 최근 1시간 Job 상태 분포 확인

```sql
SELECT status, COUNT(*)
FROM jobs
WHERE created_at >= NOW() - INTERVAL '1 hour'
GROUP BY status;
```

2. 실패 job 샘플 추출

```sql
SELECT job_id, type, status, error_message, created_at
FROM jobs
WHERE created_at >= NOW() - INTERVAL '1 hour'
  AND status IN ('failed', 'cancelled')
ORDER BY created_at DESC
LIMIT 30;
```

3. Celery 모드면 worker 상태 확인
- worker ping 실패 시 worker 재시작
- broker/backend queue 적체 확인

4. 임시 완화
- `JOB_RUNNER_MODE=inprocess`로 임시 전환(긴급 시)
- 고부하 job 입력 제한

### C. Evaluation Run 실패율 증가

증상:
- 평가 결과 파일 누락
- `run_metadata` 검증 실패

조치:
1. 실행 로그에서 `run_metadata` 생성/검증 에러 확인
2. `commit_sha`, `prompt_version`, `data_snapshot_id`, `seed`, `mode` 필수 키 누락 여부 점검
3. MLflow 사용 시 tracking URI/권한 확인
4. 동일 입력으로 단일 재실행 후 재현성 확인

## 복구 검증 체크리스트

1. `/health/detailed` 모든 구성요소 `healthy`
2. API 5xx 비율 정상화
3. Job 실패율 정상화
4. Evaluation 샘플 실행 성공 + `run_metadata` 보존 확인

## 커뮤니케이션 템플릿

### Incident 시작

- 시각: YYYY-MM-DD HH:MM KST
- 영향: (API 오류율 %, 지연, 작업 실패율)
- 영향 범위: (엔드포인트/기능)
- 임시 조치: (적용 내용)
- 다음 업데이트 예정: +30분

### Incident 종료

- 종료 시각: YYYY-MM-DD HH:MM KST
- 근본 원인: (한 줄)
- 조치 요약: (복구/완화)
- 재발 방지 과제: (담당자/기한)

## 사후 조치

- P1: 24시간 이내 포스트모템 작성
- P2: 3영업일 이내 원인 분석/개선 항목 등록
- 문서 업데이트 필요 시 `slo.md`와 본 문서를 함께 수정

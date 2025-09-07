# API v2 이용 가이드 (요약)

FastAPI v2 엔드포인트의 핵심 사용법을 요약합니다. 구현 세부와 예시는 `apps/api/README.md`와 `_archive/api-implementation-guide.md`를 참고하세요.

## 기본 정보
- Base URL(개발): `http://localhost:8001`
- 문서: `/docs`, `/redoc`
- 인증: 요청 헤더 `X-API-Key`

## 엔드포인트
- 수집(동기): `POST /api/v2/collection/`
- 수집(비동기): `POST /api/v2/collection/async`
- 수집 상태: `GET /api/v2/collection/status?date=YYYYMMDD&meet=1`
- 작업 목록: `GET /api/v2/jobs/?status=&job_type=&limit=&offset=`
- 작업 상세: `GET /api/v2/jobs/{job_id}`
- 작업 취소: `POST /api/v2/jobs/{job_id}/cancel`
- 헬스: `GET /`, `GET /health`, `GET /health/detailed`

## 예시
```bash
curl -X POST http://localhost:8001/api/v2/collection/ \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: test-api-key-123456789' \
  -d '{"date":"20250622","meet":1,"race_numbers":[1,2,3]}'
```

## 실행 팁
```bash
# 루트에서 API 개발 서버
pnpm -w -F @apps/api dev

# 또는 앱 디렉터리에서 uv 직접 실행
cd apps/api && uv run uvicorn main_v2:app --reload --port 8001
```

## 참고
- 상세 플로우/부하테스트/배포 예시: `_archive/api-implementation-guide.md`


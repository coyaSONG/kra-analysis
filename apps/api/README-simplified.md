# KRA API v2 (Simplified)

FastAPI 기반 경마 데이터 수집/작업 관리 API(v2)입니다.

## 활성 API

- `POST /api/v2/collection/`
- `POST /api/v2/collection/async`
- `GET /api/v2/collection/status`
- `GET /api/v2/jobs/`
- `GET /api/v2/jobs/{job_id}`
- `POST /api/v2/jobs/{job_id}/cancel`
- `GET /health`
- `GET /health/detailed`

## 프로젝트 구조 (요약)

```text
apps/api/
├── main_v2.py
├── routers/
│   ├── collection_v2.py
│   ├── jobs_v2.py
│   └── race.py              # legacy v1 (비활성)
├── services/
│   ├── collection_service.py
│   ├── job_service.py
│   ├── kra_api_service.py
│   └── race_service.py      # legacy v1 (비활성)
├── infrastructure/
├── middleware/
├── models/
└── tests/
```

## 실행

```bash
cd apps/api
uv sync
uv run uvicorn main_v2:app --reload --port 8000
```

## 문서

- Swagger: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Legacy v1 정책

- `routers/race.py`, `services/race_service.py`는 유지보수 대상이 아닌 legacy 코드입니다.
- 런타임 진입점(`main_v2.py`)에서는 v1 라우트를 등록하지 않습니다.

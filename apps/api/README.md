# KRA Race Prediction REST API (v2)

FastAPI 기반 경마 데이터 수집·작업 관리 REST API 서버(v2)입니다. v2는 `/api/v2/collection` 및 `/api/v2/jobs` 네임스페이스를 제공합니다.

## 기술 스택

- **FastAPI**: 웹 프레임워크
- **Supabase**: 데이터베이스 및 실시간 기능
- **Claude Code CLI**: AI 예측 엔진
- **Redis**: 캐싱 및 작업 큐
- **Celery**: 비동기 작업 처리

## 설치 및 설정

### 실행 (uv 권장) 🚀

[uv](https://github.com/astral-sh/uv)는 Rust로 작성된 초고속 Python 패키지 매니저입니다.

```bash
# uv 설치
curl -LsSf https://astral.sh/uv/install.sh | sh

# 의존성 설치 (프로젝트 루트 → 앱 디렉토리)
cd apps/api
uv sync && uv sync --dev

# 개발 서버 (기본 8000)
uv run uvicorn main_v2:app --reload --port 8000
```

모노레포 스크립트로도 실행할 수 있습니다:

```bash
# 저장소 루트에서 실행
pnpm -w -F @apps/api dev   # uvicorn main_v2:app --port 8000
```

자세한 uv 사용법은 [README-uv.md](./README-uv.md)를 참조하세요.

### pip 사용 (대안)

```bash
# 가상환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate  # macOS/Linux

# 의존성 설치
pip install -r requirements.txt
```

### 환경 변수 설정

`.env` 파일을 생성하고 다음 내용을 추가합니다:

`.env.example`를 참고하여 `.env`를 생성하세요. 필수/주요 항목:

- `SECRET_KEY` (필수)
- `DATABASE_URL` (예: `postgresql+asyncpg://user:pass@localhost:5432/kra`)
- `REDIS_URL` (예: `redis://localhost:6379/0`)
- `PORT` (개발 기본 8000)
- `VALID_API_KEYS` (선택: JSON 배열 또는 콤마 구분, 미설정 시 개발 모드에서 `test-api-key-123456789` 기본값 사용)
- `KRA_API_KEY` (선택: 공공데이터 API 키)

### 데이터베이스 설정 (선택)

Supabase 대시보드에서 SQL 에디터를 열고 `migrations/001_initial_schema.sql` 파일의 내용을 실행합니다.

### 서버 실행

```bash
# 개발 모드
uv run uvicorn main_v2:app --reload --port 8000

# 프로덕션 모드
uv run uvicorn main_v2:app --host 0.0.0.0 --port 8000 --workers 4
```

## API 엔드포인트 (v2)

### 기본 정보

- Base URL(개발): `http://localhost:8000`
- Docs: `http://localhost:8000/docs`, ReDoc: `http://localhost:8000/redoc`
- 인증: 모든 보호 엔드포인트는 헤더 `X-API-Key` 필요

### Collection

1) 경주 데이터 수집 (동기)

```
POST /api/v2/collection/
Headers: X-API-Key: test-api-key-123456789
Body:
{
  "date": "20250622",
  "meet": 1,
  "race_numbers": [1,2,3],
  "options": { "enrich": true, "get_results": false }
}
```

예시(curl)

```bash
curl -X POST http://localhost:8000/api/v2/collection/ \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: test-api-key-123456789' \
  -d '{"date":"20250622","meet":1,"race_numbers":[1,2,3]}'
```

2) 경주 데이터 수집 (비동기)

```
POST /api/v2/collection/async
Headers: X-API-Key: ...
```

응답 예시

```json
{
  "job_id": "06c2...",
  "status": "accepted",
  "message": "Collection job started",
  "webhook_url": "/api/v2/jobs/06c2...",
  "estimated_time": 5
}
```

3) 수집 상태 조회

```
GET /api/v2/collection/status?date=20250622&meet=1
Headers: X-API-Key: ...
```

### Jobs

- 목록 조회
```
GET /api/v2/jobs/?status=processing&job_type=collection&limit=20&offset=0
Headers: X-API-Key: ...
```

- 상세 조회
```
GET /api/v2/jobs/{job_id}
Headers: X-API-Key: ...
```

- 취소
```
POST /api/v2/jobs/{job_id}/cancel
Headers: X-API-Key: ...
```

### Health

- `GET /` 기본 정보, `GET /health` 헬스체크, `GET /health/detailed`(DB/Redis 상태 포함)

## 인증 가이드

- 요청 헤더 `X-API-Key` 필요. 개발/테스트 환경에서는 기본 키 `test-api-key-123456789`가 자동 허용됩니다.
- 운영 환경에서는 환경변수 `VALID_API_KEYS`에 JSON 배열 또는 콤마 구분 문자열로 키 목록을 설정하세요.

## 개발 가이드

### 프로젝트 구조 (요약)

```
apps/api/
├── main_v2.py        # 활성 런타임 진입점
├── routers/          # API 라우터
│   ├── collection_v2.py
│   ├── jobs_v2.py
│   └── race.py       # legacy v1 (비활성)
├── services/         # 서비스 계층
│   ├── collection_service.py
│   ├── job_service.py
│   ├── kra_api_service.py
│   └── race_service.py # legacy v1 (비활성)
├── infrastructure/   # DB/Redis/외부 연동
├── middleware/       # 공통 미들웨어
├── models/           # 스키마/모델
└── tests/            # 테스트
```

### 새로운 엔드포인트 추가 (가이드)

1. 서비스 로직 구현 (`services/`)
2. 라우터 추가 (`routers/`)
3. `main_v2.py`에 라우터 등록
4. 테스트 추가 (`tests/`)

### 테스트

```bash
# 전체 테스트
uv run pytest -q

# 커버리지 확인
uv run pytest --cov=. --cov-report=html
```

## Legacy v1 정책

- v1 레거시 모듈: `routers/race.py`, `services/race_service.py`
- 활성 런타임(`main_v2.py`)에는 v1 라우터를 등록하지 않습니다.
- 상세 정책: `apps/api/docs/LEGACY_V1_POLICY.md`

## 배포

### Docker를 사용한 배포

```bash
# 이미지 빌드
docker build -t kra-api .

# 컨테이너 실행
docker run -p 8000:8000 --env-file .env kra-api
```

### Docker Compose

```bash
# 전체 스택 실행 (API + Redis + Celery)
docker-compose up -d
```

## 모니터링

- 로그: 구조화된 JSON 로그 출력
- 메트릭: Prometheus 형식 (`/metrics`)
- 헬스체크: `/health`

## 주의사항

1. **API 키 보안**: 프로덕션 환경에서는 반드시 환경 변수 사용
2. **Rate Limiting**: KRA API 제한 준수 (분당 100회)
3. **Claude Code CLI**: Claude Max 구독 필요
4. **데이터 캐싱**: 7일간 말/기수/조교사 정보 캐싱

## 문제 해결

### Claude Code CLI 연결 오류
- Claude Code가 설치되어 있는지 확인
- `CLAUDE_CODE_PATH` 환경 변수 확인
- Claude에 로그인되어 있는지 확인

### Supabase 연결 오류
- Supabase URL과 키가 올바른지 확인
- 네트워크 연결 확인
- RLS 정책 확인

### Redis 연결 오류
- Redis 서버가 실행 중인지 확인
- 연결 URL이 올바른지 확인

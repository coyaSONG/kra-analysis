# KRA Race Prediction REST API

FastAPI 기반 경마 예측 시스템 REST API 서버입니다.

## 기술 스택

- **FastAPI**: 웹 프레임워크
- **Supabase**: 데이터베이스 및 실시간 기능
- **Claude Code CLI**: AI 예측 엔진
- **Redis**: 캐싱 및 작업 큐
- **Celery**: 비동기 작업 처리

## 설치 및 설정

### uv 사용 (권장) 🚀

[uv](https://github.com/astral-sh/uv)는 Rust로 작성된 초고속 Python 패키지 매니저입니다.

```bash
# uv 설치
curl -LsSf https://astral.sh/uv/install.sh | sh

# 의존성 설치 (가상환경 자동 생성)
cd api
uv sync

# 개발 환경 설정
uv sync --dev

# 서버 실행
uv run uvicorn api.main:app --reload
```

자세한 uv 사용법은 [README-uv.md](./README-uv.md)를 참조하세요.

### 기존 pip 사용

```bash
# 가상환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate  # macOS/Linux

# 의존성 설치
pip install -r requirements.txt
```

### 3. 환경 변수 설정

`.env` 파일을 생성하고 다음 내용을 추가합니다:

```env
# Supabase
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key  # Optional

# KRA API
KRA_API_KEY=your_kra_api_key

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-here-change-in-production

# Claude Code CLI
CLAUDE_CODE_PATH=/usr/local/bin/claude-code  # Claude Code CLI 경로
```

### 4. Supabase 데이터베이스 설정

Supabase 대시보드에서 SQL 에디터를 열고 `migrations/001_initial_schema.sql` 파일의 내용을 실행합니다.

### 5. 서버 실행

```bash
# 개발 모드
python -m uvicorn api.main:app --reload

# 프로덕션 모드
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API 엔드포인트

### 기본 정보

- Base URL: `http://localhost:8000`
- API Docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### 주요 엔드포인트

#### 1. 경주 데이터 수집

```bash
# 특정 날짜의 경주 수집
POST /api/v1/races/collect
{
  "date": "20250608",
  "meet": 1,
  "race_no": null  # null이면 전체 경주
}
```

#### 2. 경주 예측

```bash
# 예측 생성
POST /api/v1/predictions
{
  "race_id": "123e4567-e89b-12d3-a456-426614174000",
  "prompt_version": "base-prompt-v1.0"
}
```

#### 3. 패턴 분석

```bash
# 패턴 분석
GET /api/v1/analysis/patterns?start_date=20250601&end_date=20250630
```

#### 4. 프롬프트 개선

```bash
# 프롬프트 개선 작업 시작
POST /api/v1/improvement/improve
{
  "base_prompt_version": "base-prompt-v1.0",
  "target_date": "20250608",
  "max_iterations": 5,
  "race_limit": 20
}
```

## 개발 가이드

### 프로젝트 구조

```
api/
├── domain/           # 비즈니스 로직
├── infrastructure/   # 외부 시스템 통합
│   ├── kra_api/     # KRA API 클라이언트
│   ├── claude_cli/  # Claude Code CLI 통합
│   └── supabase_client.py
├── application/      # 애플리케이션 서비스
│   ├── services/    # 비즈니스 서비스
│   └── dto/         # 데이터 전송 객체
├── presentation/     # API 레이어
│   ├── routers/     # API 라우터
│   └── middleware/  # 미들웨어
├── config.py        # 설정
└── main.py          # 애플리케이션 진입점
```

### 새로운 엔드포인트 추가

1. DTO 정의 (`application/dto/`)
2. 서비스 로직 구현 (`application/services/`)
3. 라우터 추가 (`presentation/routers/`)
4. main.py에 라우터 등록

### 테스트

```bash
# 단위 테스트 실행
pytest

# 커버리지 확인
pytest --cov=api --cov-report=html
```

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
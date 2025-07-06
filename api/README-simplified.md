# KRA Race Prediction API (Simplified)

FastAPI 기반 경마 데이터 수집 REST API 서버입니다.

## 프로젝트 구조 (단순화됨)

```
api/
├── main.py                  # FastAPI 앱 진입점
├── config.py               # 환경 설정
├── routers/                # API 엔드포인트
│   └── race.py            # 경주 데이터 수집 API
├── services/              # 비즈니스 로직
│   └── race_service.py    # 경주 서비스
├── models/                # 데이터 모델
│   └── race_dto.py        # 데이터 전송 객체
├── middleware/            # 미들웨어
│   ├── logging.py         # 요청 로깅
│   └── rate_limit.py      # API 속도 제한
└── infrastructure/        # 외부 시스템 통합
    ├── supabase_client.py # Supabase 클라이언트
    ├── kra_api/          # KRA API 클라이언트
    └── claude_cli/       # Claude Code CLI 통합
```

## 실제 구현된 기능

### ✅ 구현 완료
- **KRA API 통합** 
  - 5개 API 엔드포인트 연동 (경주, 말, 기수, 조교사 정보)
  - JSON/XML 응답 처리
  - 재시도 및 에러 처리
- **데이터 수집 API**
  - `POST /api/v1/races/collect` - 경주 데이터 수집
  - `GET /api/v1/races/{date}` - 날짜별 경주 목록
  - `GET /api/v1/races/results/{date}/{meet}/{race_no}` - 경주 결과
- **데이터 보강 API**
  - `POST /api/v1/races/enrich/{race_id}` - 말/기수/조교사 상세 정보 추가
  - 7일 캐싱 시스템
- **인프라**
  - Supabase 데이터베이스 연동
  - 로깅 미들웨어
  - Rate Limiting (분당 100회)
  - 비동기 처리

### ⚠️ 부분 구현
- Claude CLI 통합 (구조만)
- 예측 기능 API

### ❌ 미구현
- JWT 인증/인가
- Celery 작업 큐
- 단위 테스트

## 빠른 시작

### 1. 환경 설정
```bash
# uv 사용 (권장)
uv sync

# 또는 pip 사용
pip install -r requirements.txt
```

### 2. 환경 변수
`.env` 파일 생성:
```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
KRA_API_KEY=your_kra_api_key
```

### 3. 서버 실행
```bash
# uv 사용
uv run uvicorn api.main:app --reload

# 또는 직접 실행
uvicorn api.main:app --reload
```

### 4. API 문서
- http://localhost:8000/docs

## 현재 상태

이 프로젝트는 **프로토타입** 상태입니다:
- 기본적인 API 구조만 구현
- 실제 데이터 연동 미완성
- 핵심 비즈니스 로직 부재

원래 프로젝트의 주요 기능(AI 예측, 프롬프트 개선)은 기존 스크립트 방식이 더 적합할 수 있습니다.
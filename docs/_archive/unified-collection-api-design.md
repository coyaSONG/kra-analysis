# KRA 통합 데이터 수집 API 서버 설계

## 개요

현재 개별 스크립트로 분산되어 있는 데이터 수집 및 분석 프로세스를 통합된 RESTful API 서버로 재설계합니다. 이를 통해 자동화, 확장성, 모니터링을 개선하고 운영 효율성을 높입니다.

## 현재 상태 분석

### 문제점
1. **수동 실행**: 각 스크립트를 개별적으로 실행해야 함
2. **상태 추적 어려움**: 작업 진행 상황 모니터링 불가
3. **에러 처리 미흡**: 실패 시 재시도 메커니즘 없음
4. **확장성 제한**: 병렬 처리 및 스케일링 어려움
5. **통합 부재**: Node.js와 Python 스크립트 간 연계 부족

### 기존 워크플로우
```
1. 데이터 수집 (Node.js)
   - collect_and_preprocess.js: 기본 경주 데이터
   - enrich_race_data.js: 상세 정보 보강
   - get_race_result.js: 경주 결과

2. 분석 및 예측 (Python)
   - evaluate_prompt_v3.py: 프롬프트 평가
   - predict_only_test.py: 예측 테스트
   - recursive_prompt_improvement_v5.py: 재귀 개선
```

## 통합 API 서버 아키텍처

### 시스템 구성도
```
┌─────────────────────────────────────────────────────────────┐
│                      API Gateway                            │
│                  (인증, 라우팅, 로깅)                         │
└─────────────────────────────────────────────────────────────┘
                               │
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                      │
│                                                             │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │  Collection  │  │   Analysis   │  │   Prediction    │  │
│  │   Service    │  │   Service    │  │    Service      │  │
│  └─────────────┘  └──────────────┘  └─────────────────┘  │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │               Background Job Queue                   │  │
│  │              (Celery + Redis)                       │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                               │
        ┌──────────────────────┴──────────────────────┐
        │                                              │
┌───────────────┐                            ┌────────────────┐
│   PostgreSQL  │                            │  Redis Cache   │
│   (영구저장)   │                            │   (임시저장)    │
└───────────────┘                            └────────────────┘
```

## RESTful API 엔드포인트 설계 (v2 반영)

본 섹션은 현재 구현된 v2 스펙에 맞게 갱신되었습니다. 구현되지 않은 기능은 “향후 확장(예정)”으로 이동했습니다.

### 1. 데이터 수집 API

#### 1.1 경주 데이터 수집 (동기)
```http
POST /api/v2/collection/
Content-Type: application/json

{
  "date": "20250622",
  "meet": 1,
  "race_numbers": [1, 2, 3],
  "options": {
    "enrich": true,
    "get_results": false
  }
}

Response (예시):
{
  "status": "success",
  "message": "Collected 3 races",
  "data": [ ... ]
}
```

#### 1.2 경주 데이터 수집 (비동기)
```http
POST /api/v2/collection/async

Response (예시):
{
  "job_id": "06c2...",
  "status": "accepted",
  "message": "Collection job started",
  "webhook_url": "/api/v2/jobs/06c2...",
  "estimated_time": 5
}
```

#### 1.3 수집 상태 조회
```http
GET /api/v2/collection/status?date=20250622&meet=1
```

### 2. 작업 관리 API

```http
# 목록 조회
GET /api/v2/jobs/?status=processing&job_type=collection&limit=20&offset=0

# 상세 조회
GET /api/v2/jobs/{job_id}

# 취소 (메서드 변경: POST)
POST /api/v2/jobs/{job_id}/cancel
```

### 3. 모니터링 API

```http
GET /health           # 간단 헬스체크
GET /health/detailed  # DB/Redis 상태 포함
```

### 4. 향후 확장 (예정)

- 데이터 보강 전용 엔드포인트: `POST /api/v2/collection/enrich`
- 경주 결과 수집: `POST /api/v2/collection/results`
- 데이터 조회: `GET /api/v2/races`, `GET /api/v2/races/{race_id}`
- 분석/예측: `POST /api/v2/analysis/evaluate`, `POST /api/v2/prediction/run`, `POST /api/v2/analysis/improve-prompt`

현재 리포지토리에는 상기 엔드포인트가 구현되어 있지 않습니다. 필요한 경우 로드맵에 따라 순차 구현하세요.

## 비동기 작업 처리 시스템

### Celery 작업 정의
```python
# tasks/collection.py
@celery_task(bind=True, max_retries=3)
def collect_race_data(self, date: str, meet: int, race_numbers: List[int]):
    """경주 데이터 수집 작업"""
    try:
        for race_no in race_numbers:
            # 진행률 업데이트
            self.update_state(
                state='PROGRESS',
                meta={'current': race_no, 'total': len(race_numbers)}
            )
            
            # 데이터 수집
            data = kra_client.get_race_data(date, meet, race_no)
            
            # 저장
            save_race_data(data)
            
            # 자동 보강 옵션 확인
            if self.request.kwargs.get('auto_enrich'):
                enrich_race_data.delay(race_id)
                
    except Exception as exc:
        # 재시도
        raise self.retry(exc=exc, countdown=60)

# tasks/analysis.py
@celery_task
def evaluate_prompt_async(prompt_id: str, race_ids: List[str]):
    """프롬프트 평가 작업"""
    evaluator = PromptEvaluator(prompt_id)
    results = evaluator.evaluate_races(race_ids)
    
    # 결과 저장
    save_evaluation_results(prompt_id, results)
    
    # 웹훅 알림
    notify_webhook(results)
```

### 작업 스케줄링
```python
# celery_beat_schedule.py
from celery.schedules import crontab

beat_schedule = {
    # 매일 오전 6시 전날 데이터 수집
    'daily-collection': {
        'task': 'tasks.collection.collect_yesterday_races',
        'schedule': crontab(hour=6, minute=0),
    },
    
    # 매주 월요일 주간 분석 실행
    'weekly-analysis': {
        'task': 'tasks.analysis.weekly_performance_analysis',
        'schedule': crontab(hour=9, minute=0, day_of_week=1),
    },
    
    # 매시간 캐시 정리
    'hourly-cleanup': {
        'task': 'tasks.maintenance.cleanup_old_cache',
        'schedule': crontab(minute=0),
    }
}
```

## 데이터 모델 설계

### 1. 작업(Job) 모델
```python
class Job(BaseModel):
    job_id: str = Field(primary_key=True)
    type: JobType  # collection, enrichment, analysis, prediction
    status: JobStatus  # queued, processing, completed, failed, cancelled
    
    # 메타데이터
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    # 진행 상황
    progress: int = Field(default=0, ge=0, le=100)
    current_step: Optional[str]
    total_steps: Optional[int]
    
    # 결과
    result: Optional[Dict[str, Any]]
    error_message: Optional[str]
    retry_count: int = Field(default=0)
    
    # 관계
    user_id: Optional[str]
    related_jobs: List[str] = Field(default_factory=list)
```

### 2. 경주 데이터 모델
```python
class Race(BaseModel):
    race_id: str = Field(primary_key=True)
    date: str
    meet: int
    race_number: int
    
    # 상태
    collection_status: DataStatus
    enrichment_status: DataStatus
    result_status: DataStatus
    
    # 데이터
    basic_data: Dict[str, Any]
    enriched_data: Optional[Dict[str, Any]]
    result_data: Optional[RaceResult]
    
    # 타임스탬프
    collected_at: datetime
    enriched_at: Optional[datetime]
    result_collected_at: Optional[datetime]
    
    # 메타데이터
    data_quality_score: float = Field(ge=0, le=1)
    warnings: List[str] = Field(default_factory=list)
```

### 3. 예측 모델
```python
class Prediction(BaseModel):
    prediction_id: str = Field(primary_key=True)
    race_id: str
    prompt_id: str
    
    # 예측 결과
    predicted_positions: List[int]  # [1st, 2nd, 3rd]
    confidence: int = Field(ge=0, le=100)
    reasoning: str
    
    # 평가
    actual_result: Optional[List[int]]
    accuracy_score: Optional[float]
    
    # 메타데이터
    created_at: datetime
    execution_time_ms: int
    model_version: str
```

## 보안 및 인증

### JWT 기반 인증
```python
# auth/jwt.py
from fastapi_jwt_auth import AuthJWT

class JWTSettings(BaseModel):
    authjwt_secret_key: str = settings.SECRET_KEY
    authjwt_token_location: set = {"headers", "cookies"}
    authjwt_cookie_secure: bool = True
    authjwt_cookie_httponly: bool = True

@AuthJWT.load_config
def get_config():
    return JWTSettings()

# 보호된 엔드포인트
@router.post("/collection/races")
async def collect_races(
    request: CollectionRequest,
    Authorize: AuthJWT = Depends()
):
    Authorize.jwt_required()
    user_id = Authorize.get_jwt_subject()
    
    # 권한 확인
    if not has_permission(user_id, "collection:write"):
        raise HTTPException(403, "권한 없음")
```

### API 키 관리
```python
# middleware/api_key.py
class APIKeyMiddleware:
    async def __call__(self, request: Request, call_next):
        api_key = request.headers.get("X-API-Key")
        
        if not api_key:
            return JSONResponse(
                status_code=401,
                content={"error": "API 키 필요"}
            )
        
        # 키 검증
        key_info = await verify_api_key(api_key)
        if not key_info:
            return JSONResponse(
                status_code=401,
                content={"error": "유효하지 않은 API 키"}
            )
        
        # 사용량 확인
        if await check_rate_limit(key_info):
            return JSONResponse(
                status_code=429,
                content={"error": "요청 한도 초과"}
            )
        
        # 요청 처리
        request.state.api_key_info = key_info
        response = await call_next(request)
        
        # 사용량 기록
        await record_usage(key_info, request, response)
        
        return response
```

## 에러 처리 및 재시도

### 전역 에러 핸들러
```python
# middleware/error_handler.py
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_id = str(uuid.uuid4())
    
    # 로깅
    logger.error(f"Error {error_id}: {exc}", exc_info=True)
    
    # 에러 분류
    if isinstance(exc, ValidationError):
        return JSONResponse(
            status_code=400,
            content={
                "error": "검증 실패",
                "details": exc.errors(),
                "error_id": error_id
            }
        )
    elif isinstance(exc, KRAAPIError):
        return JSONResponse(
            status_code=502,
            content={
                "error": "외부 API 오류",
                "message": str(exc),
                "error_id": error_id
            }
        )
    else:
        return JSONResponse(
            status_code=500,
            content={
                "error": "서버 오류",
                "error_id": error_id,
                "message": "관리자에게 문의하세요"
            }
        )
```

### 재시도 전략
```python
# utils/retry.py
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def call_kra_api(endpoint: str, params: dict):
    """KRA API 호출 with 재시도"""
    async with httpx.AsyncClient() as client:
        response = await client.get(endpoint, params=params)
        response.raise_for_status()
        return response.json()
```

## 모니터링 및 로깅

### 구조화된 로깅
```python
# logging/structured.py
import structlog

logger = structlog.get_logger()

# 요청 로깅
@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())
    
    # 요청 컨텍스트 바인딩
    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        user_id=getattr(request.state, "user_id", None)
    )
    
    start_time = time.time()
    
    # 요청 로그
    logger.info("request_started")
    
    # 응답 처리
    response = await call_next(request)
    
    # 응답 로그
    duration = time.time() - start_time
    logger.info(
        "request_completed",
        status_code=response.status_code,
        duration_ms=duration * 1000
    )
    
    # 헤더 추가
    response.headers["X-Request-ID"] = request_id
    
    return response
```

### Prometheus 메트릭
```python
# monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# 메트릭 정의
request_count = Counter(
    'api_requests_total',
    '총 API 요청 수',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'api_request_duration_seconds',
    'API 요청 처리 시간',
    ['method', 'endpoint']
)

active_jobs = Gauge(
    'active_jobs_count',
    '활성 작업 수',
    ['job_type']
)

# 메트릭 수집
@app.middleware("http")
async def collect_metrics(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    # 메트릭 업데이트
    request_count.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    request_duration.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(time.time() - start_time)
    
    return response
```

## 배포 전략

### Docker 컨테이너화
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 복사
COPY . .

# 헬스체크
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Kubernetes 배포
```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kra-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: kra-api
  template:
    metadata:
      labels:
        app: kra-api
    spec:
      containers:
      - name: api
        image: kra-api:latest
        ports:
        - containerPort: 8001
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: kra-secrets
              key: database-url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8001
          initialDelaySeconds: 30
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: kra-api-service
spec:
  selector:
    app: kra-api
  ports:
  - port: 80
    targetPort: 8001
  type: LoadBalancer
```

## 마이그레이션 계획

### 1단계: API 서버 구축 (1주)
- FastAPI 애플리케이션 구조 설정
- 기본 엔드포인트 구현
- Celery 작업 큐 설정
- 데이터베이스 모델 구현

### 2단계: 기능 이전 (2-3주)
- 데이터 수집 기능 이전
- 보강 프로세스 구현
- 분석 및 예측 API 구현
- 기존 스크립트와 병행 운영

### 3단계: 테스트 및 최적화 (1주)
- 통합 테스트
- 성능 최적화
- 에러 처리 개선
- 문서화

### 4단계: 전환 (1주)
- 점진적 트래픽 이전
- 모니터링 강화
- 이슈 대응
- 기존 스크립트 폐기

## API 문서화 (OpenAPI)

```python
# main.py
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

app = FastAPI(
    title="KRA 데이터 수집 및 분석 API",
    description="경마 데이터 수집, 분석, 예측을 위한 통합 API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="KRA Analysis API",
        version="1.0.0",
        description="""
        ## 개요
        KRA 경마 데이터 수집 및 분석을 위한 RESTful API
        
        ## 인증
        - API Key: 헤더에 X-API-Key 포함
        - JWT: Bearer 토큰 사용
        
        ## 주요 기능
        1. 데이터 수집 - 경주, 말, 기수 정보
        2. 데이터 분석 - 패턴 분석, 성능 평가
        3. 예측 실행 - AI 기반 삼복연승 예측
        """,
        routes=app.routes
    )
    
    # 보안 스키마 추가
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key"
        },
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer"
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
```

## 성능 목표

### API 응답 시간
- 일반 조회: < 100ms (P95)
- 복잡한 쿼리: < 500ms (P95)
- 작업 생성: < 200ms (P95)

### 처리량
- 동시 요청: 1000+ RPS
- 동시 작업: 100+ 작업
- 일일 처리량: 100,000+ 경주

### 가용성
- Uptime: 99.9%
- 자동 복구: < 1분
- 데이터 일관성: 100%

## 결론

이 설계를 통해 현재의 수동적이고 분산된 스크립트 실행 방식을 자동화되고 확장 가능한 RESTful API 서버로 전환할 수 있습니다. 주요 이점:

1. **자동화**: 스케줄링 및 워크플로우 자동화
2. **확장성**: 수평적 확장 가능
3. **모니터링**: 실시간 상태 추적
4. **신뢰성**: 에러 처리 및 재시도
5. **통합성**: 단일 API로 모든 기능 접근

다음 단계는 이 설계를 바탕으로 실제 구현을 시작하는 것입니다.

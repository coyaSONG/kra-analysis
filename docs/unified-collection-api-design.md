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

## RESTful API 엔드포인트 설계

### 1. 데이터 수집 API

#### 1.1 경주 데이터 수집
```http
POST /api/v1/collection/races
Content-Type: application/json

{
  "date": "20250622",
  "meet": 1,  // 1: 서울, 2: 제주, 3: 부산경남
  "race_numbers": [1, 2, 3],  // 생략시 전체
  "options": {
    "enrich": true,  // 자동 보강 여부
    "get_results": false  // 결과 수집 여부
  }
}

Response:
{
  "job_id": "col_20250622_1_abc123",
  "status": "queued",
  "estimated_time": 180,
  "webhook_url": "/api/v1/jobs/col_20250622_1_abc123"
}
```

#### 1.2 데이터 보강
```http
POST /api/v1/collection/enrich
Content-Type: application/json

{
  "race_ids": ["race_1_20250622_1"],
  "enrich_types": ["horse", "jockey", "trainer"]
}

Response:
{
  "job_id": "enr_20250622_xyz789",
  "status": "processing",
  "races_queued": 1
}
```

#### 1.3 경주 결과 수집
```http
POST /api/v1/collection/results
Content-Type: application/json

{
  "date": "20250622",
  "meet": 1,
  "race_number": 1
}

Response:
{
  "job_id": "res_20250622_1_1_def456",
  "status": "completed",
  "result": {
    "1st": 5,
    "2nd": 3,
    "3rd": 7
  }
}
```

### 2. 데이터 조회 API

#### 2.1 경주 데이터 조회
```http
GET /api/v1/races?date=20250622&meet=1&enriched=true

Response:
{
  "races": [
    {
      "race_id": "race_1_20250622_1",
      "date": "20250622",
      "meet": 1,
      "race_number": 1,
      "status": "enriched",
      "horses": [...],
      "enriched_data": {...}
    }
  ],
  "total": 11,
  "page": 1
}
```

#### 2.2 개별 경주 상세
```http
GET /api/v1/races/{race_id}

Response:
{
  "race_id": "race_1_20250622_1",
  "basic_data": {...},
  "enriched_data": {
    "horses": [...],
    "jockeys": [...],
    "trainers": [...]
  },
  "result": {
    "1st": 5,
    "2nd": 3,
    "3rd": 7
  }
}
```

### 3. 분석 및 예측 API

#### 3.1 프롬프트 평가
```http
POST /api/v1/analysis/evaluate
Content-Type: application/json

{
  "prompt_id": "base-prompt-v1.0",
  "race_ids": ["race_1_20250622_1", "race_1_20250622_2"],
  "parallel_count": 3
}

Response:
{
  "job_id": "eval_prompt_v1.0_ghi789",
  "status": "processing",
  "estimated_time": 300
}
```

#### 3.2 예측 실행
```http
POST /api/v1/prediction/run
Content-Type: application/json

{
  "race_id": "race_1_20250622_1",
  "prompt_id": "base-prompt-v1.0",
  "options": {
    "confidence_threshold": 70
  }
}

Response:
{
  "prediction_id": "pred_20250622_1_1_jkl012",
  "predicted": [5, 3, 7],
  "confidence": 75,
  "reasoning": "인기마 중심, 기수 능력 우수"
}
```

#### 3.3 재귀적 프롬프트 개선
```http
POST /api/v1/analysis/improve-prompt
Content-Type: application/json

{
  "initial_prompt_id": "base-prompt-v1.0",
  "iterations": 5,
  "race_sample_size": 20,
  "target_date": "all"
}

Response:
{
  "job_id": "imp_v1.0_to_v2.0_mno345",
  "status": "queued",
  "estimated_hours": 2
}
```

### 4. 작업 관리 API

#### 4.1 작업 상태 조회
```http
GET /api/v1/jobs/{job_id}

Response:
{
  "job_id": "col_20250622_1_abc123",
  "type": "collection",
  "status": "processing",
  "progress": 65,
  "current_step": "enriching_data",
  "started_at": "2025-06-22T10:00:00Z",
  "estimated_completion": "2025-06-22T10:03:00Z",
  "logs": [
    {
      "timestamp": "2025-06-22T10:00:05Z",
      "message": "Started collecting race 1"
    }
  ]
}
```

#### 4.2 작업 취소
```http
DELETE /api/v1/jobs/{job_id}

Response:
{
  "job_id": "col_20250622_1_abc123",
  "status": "cancelled",
  "cancelled_at": "2025-06-22T10:01:30Z"
}
```

#### 4.3 작업 목록
```http
GET /api/v1/jobs?status=processing&type=collection&limit=10

Response:
{
  "jobs": [
    {
      "job_id": "col_20250622_1_abc123",
      "type": "collection",
      "status": "processing",
      "progress": 65
    }
  ],
  "total": 3,
  "page": 1
}
```

### 5. 모니터링 API

#### 5.1 시스템 상태
```http
GET /api/v1/monitoring/health

Response:
{
  "status": "healthy",
  "services": {
    "api": "up",
    "database": "up",
    "redis": "up",
    "celery": "up"
  },
  "metrics": {
    "active_jobs": 5,
    "queued_jobs": 12,
    "api_response_time_ms": 45
  }
}
```

#### 5.2 실시간 상태 (WebSocket)
```javascript
ws://api.kra-analysis.com/ws/monitoring

// 구독
{
  "action": "subscribe",
  "channels": ["jobs", "system"]
}

// 실시간 업데이트
{
  "channel": "jobs",
  "event": "status_change",
  "data": {
    "job_id": "col_20250622_1_abc123",
    "old_status": "queued",
    "new_status": "processing"
  }
}
```

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
    CMD curl -f http://localhost:8000/api/v1/monitoring/health || exit 1

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
        - containerPort: 8000
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
            path: /api/v1/monitoring/health
            port: 8000
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
    targetPort: 8000
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

현재 활성 FastAPI 진입점은 `apps/api/main_v2.py`이며, OpenAPI 문서는 `GET /docs`와 `GET /openapi.json`으로 제공합니다.
활성 라우트는 v2 기준(`collection_v2`, `jobs_v2`)이며, 이 문서의 기존 `main.py`/v1 예시는 레거시 설계 참고용입니다.

```python
# main_v2.py (active runtime)
app = FastAPI(
    title='KRA Race Prediction API',
    version='2.0.0',
    docs_url='/docs',
    redoc_url='/redoc',
    openapi_url='/openapi.json',
)
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

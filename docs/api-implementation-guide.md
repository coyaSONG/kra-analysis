# KRA 통합 API 구현 가이드

## 개요

이 문서는 설계된 통합 API 서버를 실제로 구현하기 위한 단계별 가이드입니다.

## 구현 로드맵

### Phase 1: 기반 구축 (1주차)

#### 1.1 프로젝트 구조 설정

```bash
# 새로운 API 프로젝트 구조
api/
├── main_v2.py              # 메인 애플리케이션
├── config.py               # 설정 관리
├── dependencies/           # 의존성 주입
│   ├── __init__.py
│   └── auth.py            # 인증 의존성
├── infrastructure/         # 인프라 계층
│   ├── __init__.py
│   ├── database.py        # DB 연결
│   ├── redis_client.py    # Redis 연결
│   └── celery_app.py      # Celery 설정
├── middleware/            # 미들웨어
│   ├── __init__.py
│   ├── auth.py           # 인증 미들웨어
│   ├── logging.py        # 로깅 미들웨어
│   └── rate_limit.py     # 속도 제한
├── models/               # 데이터 모델
│   ├── __init__.py
│   ├── collection_dto.py # 수집 DTO
│   └── job_dto.py       # 작업 DTO
├── routers/             # API 라우터
│   ├── __init__.py
│   ├── collection_v2.py # 수집 API
│   ├── analysis_v2.py   # 분석 API
│   ├── prediction_v2.py # 예측 API
│   ├── jobs_v2.py       # 작업 관리
│   └── monitoring_v2.py # 모니터링
├── services/            # 비즈니스 로직
│   ├── __init__.py
│   ├── collection_service.py
│   ├── job_service.py
│   └── kra_api_service.py
├── tasks/              # Celery 작업
│   ├── __init__.py
│   ├── collection_tasks.py
│   └── analysis_tasks.py
└── tests/              # 테스트
    ├── __init__.py
    └── test_collection.py
```

#### 1.2 의존성 설치

```bash
# requirements.txt 업데이트
pip install fastapi[all]==0.115.5
pip install celery[redis]==5.4.0
pip install httpx==0.28.0
pip install structlog==24.4.0
pip install prometheus-client==0.21.0

# 개발 도구
pip install pytest-asyncio==0.25.0
pip install black==24.10.0
pip install ruff>=0.8.0
```

#### 1.3 환경 설정

```bash
# .env 파일 설정
DATABASE_URL=postgresql://user:pass@localhost/kra_db
REDIS_URL=redis://localhost:6379
CELERY_BROKER_URL=redis://localhost:6379/1
KRA_SERVICE_KEY=your_api_key
SECRET_KEY=your_secret_key_for_jwt
ALLOWED_ORIGINS=http://localhost:3000,https://app.kra-analysis.com
LOG_LEVEL=INFO
```

### Phase 2: 핵심 기능 구현 (2-3주차)

#### 2.1 KRA API 서비스 구현

```python
# services/kra_api_service.py
import httpx
from typing import Optional, Dict, Any
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()

class KRAApiService:
    """KRA 공공 API 클라이언트"""
    
    def __init__(self):
        self.base_url = "https://apis.data.go.kr/B551015"
        self.api_key = settings.kra_api_key
        self.timeout = httpx.Timeout(30.0)
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def get_race_data(
        self, 
        date: str, 
        meet: int, 
        race_no: int
    ) -> Optional[Dict[str, Any]]:
        """경주 데이터 조회"""
        url = f"{self.base_url}/API214_1/RaceDetailResult_1"
        params = {
            "serviceKey": self.api_key,
            "numOfRows": 50,
            "pageNo": 1,
            "meet": meet,
            "rc_date": date,
            "rc_no": race_no,
            "_type": "json"
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            if data['response']['header']['resultCode'] == '00':
                return data
            
            return None
```

#### 2.2 데이터베이스 모델 구현

```python
# infrastructure/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

SQLALCHEMY_DATABASE_URL = settings.database_url

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=settings.debug,
    pool_size=20,
    max_overflow=40
)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

#### 2.3 Redis 캐싱 구현

```python
# services/cache_service.py
import redis.asyncio as redis
import json
from typing import Optional, Any

class CacheService:
    def __init__(self):
        self.redis = redis.from_url(
            settings.redis_url,
            decode_responses=True
        )
        
    async def get(self, key: str) -> Optional[Any]:
        """캐시 조회"""
        value = await self.redis.get(key)
        if value:
            return json.loads(value)
        return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: int = 3600
    ):
        """캐시 저장"""
        await self.redis.setex(
            key,
            ttl,
            json.dumps(value, ensure_ascii=False)
        )
    
    async def delete(self, key: str):
        """캐시 삭제"""
        await self.redis.delete(key)
```

### Phase 3: 마이그레이션 전략 (4주차)

#### 3.1 단계별 마이그레이션

##### Step 1: 병렬 운영 준비
```bash
# 1. 새 API 서버 실행
uvicorn api.main_v2:app --reload --port 8001

# 2. Celery 워커 실행
celery -A api.tasks worker --loglevel=info

# 3. Celery Beat 실행 (스케줄링)
celery -A api.tasks beat --loglevel=info
```

##### Step 2: 기존 스크립트 래퍼 생성
```python
# migration/script_wrapper.py
"""기존 스크립트를 API로 래핑"""

@router.post("/legacy/collect")
async def legacy_collect(date: str, meet: int):
    """기존 Node.js 스크립트 실행"""
    cmd = f"node scripts/race_collector/collect_and_preprocess.js {date} {meet}"
    
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()
    
    if process.returncode == 0:
        return {"status": "success", "output": stdout.decode()}
    else:
        raise HTTPException(500, detail=stderr.decode())
```

##### Step 3: 점진적 전환
```python
# 트래픽 분할 예시
import random

@router.post("/collection/races")
async def collect_races_with_migration(request: CollectionRequest):
    # 10% 트래픽을 새 시스템으로
    if random.random() < 0.1:
        return await new_collection_endpoint(request)
    else:
        return await legacy_collection_wrapper(request)
```

#### 3.2 데이터 마이그레이션

```python
# migration/data_migration.py
async def migrate_existing_data():
    """기존 JSON 파일을 DB로 마이그레이션"""
    
    # 1. 기존 파일 스캔
    race_files = glob.glob("data/races/*/*/*/*/*_enriched.json")
    
    for file_path in race_files:
        # 2. JSON 데이터 로드
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # 3. DB에 저장
        race = Race(
            race_id=extract_race_id(file_path),
            data=data,
            status="migrated"
        )
        
        async with get_db() as session:
            session.add(race)
            await session.commit()
```

### Phase 4: 테스트 및 검증 (5주차)

#### 4.1 통합 테스트

```python
# tests/test_integration.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_collection_workflow():
    """전체 수집 워크플로우 테스트"""
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 1. 수집 시작
        response = await client.post(
            "/api/v2/collection/races",
            json={
                "date": "20250622",
                "meet": 1
            },
            headers={"X-API-Key": "test_key"}
        )
        
        assert response.status_code == 200
        job_id = response.json()["job_id"]
        
        # 2. 상태 확인
        response = await client.get(
            f"/api/v2/jobs/{job_id}",
            headers={"X-API-Key": "test_key"}
        )
        
        assert response.status_code == 200
        assert response.json()["status"] in ["queued", "processing"]
```

#### 4.2 성능 테스트

```bash
# Locust를 사용한 부하 테스트
pip install locust

# locustfile.py
from locust import HttpUser, task, between

class KRAApiUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def get_races(self):
        self.client.get(
            "/api/v2/collection/races?date=20250622",
            headers={"X-API-Key": "test_key"}
        )
    
    @task
    def create_collection(self):
        self.client.post(
            "/api/v2/collection/races",
            json={"date": "20250622", "meet": 1},
            headers={"X-API-Key": "test_key"}
        )

# 실행
locust -f locustfile.py --host=http://localhost:8000
```

### Phase 5: 배포 및 운영 (6주차)

#### 5.1 Docker 이미지 빌드

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션
COPY . .

# 헬스체크
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 실행
CMD ["uvicorn", "api.main_v2:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 5.2 Docker Compose 설정

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://kra:password@postgres:5432/kra_db
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  celery-worker:
    build: .
    command: celery -A api.tasks worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql://kra:password@postgres:5432/kra_db
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis

  celery-beat:
    build: .
    command: celery -A api.tasks beat --loglevel=info
    environment:
      - DATABASE_URL=postgresql://kra:password@postgres:5432/kra_db
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: kra_db
      POSTGRES_USER: kra
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

## 모니터링 설정

### Prometheus 메트릭 수집

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'kra-api'
    static_configs:
      - targets: ['api:8000']
```

### Grafana 대시보드

```json
{
  "dashboard": {
    "title": "KRA API Monitoring",
    "panels": [
      {
        "title": "API Response Time",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, api_request_duration_seconds_bucket)"
          }
        ]
      },
      {
        "title": "Active Jobs",
        "targets": [
          {
            "expr": "active_jobs_count"
          }
        ]
      }
    ]
  }
}
```

## 운영 체크리스트

### 배포 전 확인사항

- [ ] 모든 테스트 통과
- [ ] 환경 변수 설정 완료
- [ ] 데이터베이스 마이그레이션 완료
- [ ] Redis 연결 확인
- [ ] API 키 설정
- [ ] CORS 설정 확인
- [ ] 로깅 설정 확인
- [ ] 헬스체크 엔드포인트 동작 확인

### 배포 후 확인사항

- [ ] 모든 엔드포인트 응답 확인
- [ ] Celery 워커 동작 확인
- [ ] 스케줄된 작업 동작 확인
- [ ] 모니터링 대시보드 확인
- [ ] 로그 수집 확인
- [ ] 알림 설정 확인

## 트러블슈팅

### 일반적인 문제 해결

1. **Celery 작업이 실행되지 않음**
   ```bash
   # 워커 상태 확인
   celery -A api.tasks inspect active
   
   # 큐 상태 확인
   celery -A api.tasks inspect reserved
   ```

2. **Redis 연결 오류**
   ```python
   # Redis 연결 테스트
   import redis
   r = redis.Redis.from_url("redis://localhost:6379")
   r.ping()  # True 반환되어야 함
   ```

3. **API 응답 지연**
   - 데이터베이스 인덱스 확인
   - Redis 캐시 히트율 확인
   - 동시 요청 수 제한 조정

## 결론

이 가이드를 따라 단계적으로 구현하면 안정적인 통합 API 서버를 구축할 수 있습니다. 각 단계마다 충분한 테스트를 거치고, 점진적으로 트래픽을 이전하여 위험을 최소화하세요.

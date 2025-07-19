"""
KRA 통합 데이터 수집 API 서버 v2
모든 데이터 수집 및 분석 기능을 RESTful API로 제공
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import structlog
import time
import uuid
import os
import asyncio

from config import settings
from middleware.logging import RequestLoggingMiddleware
from middleware.rate_limit import RateLimitMiddleware
from routers import (
    collection_v2,
    jobs_v2
)
from infrastructure.database import init_db, close_db
from infrastructure.redis_client import init_redis, close_redis

# Celery는 선택적으로 로드
try:
    from infrastructure.celery_app import celery_app
    CELERY_AVAILABLE = True
except Exception:
    CELERY_AVAILABLE = False

# 구조화된 로깅 설정
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.contextvars.merge_contextvars,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


async def create_required_directories():
    """필요한 디렉토리들을 생성"""
    directories = [
        settings.data_dir, 
        settings.cache_dir, 
        settings.prompts_dir, 
        settings.logs_dir
    ]
    
    for dir_path in directories:
        try:
            os.makedirs(dir_path, exist_ok=True)
            logger.info(f"Directory created or verified: {dir_path}")
        except Exception as e:
            logger.error(f"Failed to create directory {dir_path}: {e}")
            # Continue with other directories even if one fails


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    # 시작
    logger.info(
        "Starting KRA Unified API Server",
        version=settings.version,
        environment=settings.environment
    )
    
    # 필요한 디렉토리 생성
    await create_required_directories()
    
    # 초기화
    await init_db()
    await init_redis()
    
    # Celery 워커 상태 확인 (선택적)
    if CELERY_AVAILABLE:
        try:
            celery_status = celery_app.control.inspect().active()
            if celery_status:
                logger.info(f"Celery workers active: {len(celery_status)} nodes")
            else:
                logger.warning("No active Celery workers detected")
        except Exception as e:
            logger.warning(f"Could not check Celery status: {e}")
    else:
        logger.info("Running without Celery workers")
    
    yield
    
    # 종료
    logger.info("Shutting down KRA Unified API Server")
    await close_db()
    await close_redis()


# FastAPI 앱 생성
app = FastAPI(
    title="KRA 통합 데이터 수집 API",
    description="""
    ## 개요
    경마 데이터 수집, 분석, 예측을 위한 통합 RESTful API
    
    ## 주요 기능
    - **데이터 수집**: 경주, 말, 기수, 조교사 정보 자동 수집
    - **데이터 분석**: AI 기반 패턴 분석 및 인사이트 도출
    - **예측 실행**: 삼복연승 예측 및 평가
    - **작업 관리**: 비동기 작업 실행 및 모니터링
    
    ## 인증
    - API Key: 헤더에 `X-API-Key` 포함
    - JWT: Bearer 토큰 사용 (선택적)
    """,
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "collection",
            "description": "데이터 수집 관련 API"
        },
        {
            "name": "jobs",
            "description": "작업 관리 API"
        }
    ]
)

# 미들웨어 추가
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimitMiddleware, calls=100, period=60)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# 라우터 포함
app.include_router(
    collection_v2.router,
    prefix="/api/v2/collection",
    tags=["collection"]
)
app.include_router(
    jobs_v2.router,
    prefix="/api/v2/jobs",
    tags=["jobs"]
)


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "service": "KRA Unified Collection API",
        "version": "2.0.0",
        "status": "operational",
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json"
        },
        "endpoints": {
            "collection": "/api/v2/collection",
            "jobs": "/api/v2/jobs"
        }
    }


@app.get("/health")
async def health_check():
    """간단한 헬스체크"""
    return {
        "status": "healthy",
        "timestamp": time.time()
    }


# 전역 에러 핸들러
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """전역 예외 처리"""
    error_id = str(uuid.uuid4())
    
    logger.error(
        f"Unhandled exception",
        error_id=error_id,
        exception=str(exc),
        path=request.url.path,
        method=request.method
    )
    
    return JSONResponse(
        content={
            "error": "Internal server error",
            "error_id": error_id,
            "message": "An unexpected error occurred. Please contact support with the error ID."
        },
        status_code=500
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main_v2:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=False  # 커스텀 로깅 사용
    )
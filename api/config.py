"""
통합 API 서버 설정 관리
환경 변수 및 애플리케이션 설정
"""

from pydantic_settings import BaseSettings
from functools import lru_cache
import os
from typing import Optional, List


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # Application
    app_name: str = "KRA Unified Collection API"
    version: str = "2.0.0"
    environment: str = "development"
    debug: bool = True
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    
    # Database
    database_url: str = "postgresql+asyncpg://kra_user:kra_password@localhost:5432/kra_analysis"
    database_pool_size: int = 20
    database_max_overflow: int = 40
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl: int = 3600  # 1 hour
    
    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    celery_task_default_queue: str = "kra_tasks"
    celery_task_acks_late: bool = True
    celery_worker_prefetch_multiplier: int = 1
    
    # KRA API
    kra_api_base_url: str = "https://apis.data.go.kr/B551015"
    kra_api_key: Optional[str] = None  # 환경변수: KRA_API_KEY
    kra_api_timeout: int = 30
    kra_api_max_retries: int = 3
    kra_rate_limit: int = 100  # requests per minute
    
    # Security
    secret_key: str = "your-secret-key-here-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    api_key_header: str = "X-API-Key"
    
    # CORS
    allowed_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "https://app.kra-analysis.com"
    ]
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    log_file: Optional[str] = "logs/api.log"
    
    # File Storage
    data_dir: str = "./data"
    cache_dir: str = "./data/cache"
    prompts_dir: str = "./prompts"
    logs_dir: str = "./logs"
    
    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_calls: int = 100
    rate_limit_period: int = 60  # seconds
    
    # Monitoring
    prometheus_enabled: bool = True
    prometheus_port: int = 9090
    
    # Claude API (제거됨 - Claude Code 직접 사용)
    
    # Task Configuration
    collection_task_timeout: int = 300  # 5 minutes
    enrichment_task_timeout: int = 600  # 10 minutes
    
    # API Keys (for demo/testing)
    valid_api_keys: List[str] = [
        "demo-key-123",
        "test-key-456"
    ]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
        # 환경 변수 매핑
        fields = {
            "database_url": {"env": "DATABASE_URL"},
            "redis_url": {"env": "REDIS_URL"},
            "kra_service_key": {"env": "KRA_SERVICE_KEY"},
            "secret_key": {"env": "SECRET_KEY"},
        }


@lru_cache()
def get_settings() -> Settings:
    """설정 싱글톤 인스턴스 반환"""
    return Settings()


# 전역 설정 인스턴스
settings = get_settings()


# 환경별 설정 오버라이드
if settings.environment == "production":
    settings.debug = False
    settings.log_level = "WARNING"
    settings.workers = 8
elif settings.environment == "staging":
    settings.debug = False
    settings.log_level = "INFO"
    settings.workers = 4


# 디렉토리 생성
for dir_path in [settings.data_dir, settings.cache_dir, settings.prompts_dir, settings.logs_dir]:
    os.makedirs(dir_path, exist_ok=True)
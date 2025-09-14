"""
통합 API 서버 설정 관리
환경 변수 및 애플리케이션 설정
"""

import os
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


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
    database_url: str = (
        "postgresql+asyncpg://kra_user:kra_password@localhost:5432/kra_analysis"
    )
    database_pool_size: int = 20
    database_max_overflow: int = 40

    # Supabase
    supabase_url: str = Field(default="your_supabase_url", env="SUPABASE_URL")
    supabase_key: str = Field(default="your_supabase_anon_key", env="SUPABASE_ANON_KEY")
    supabase_service_role_key: str | None = Field(
        default=None, env="SUPABASE_SERVICE_ROLE_KEY"
    )

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
    kra_api_base_url: str = "http://apis.data.go.kr/B551015"
    kra_api_key: str | None = None  # 환경변수: KRA_API_KEY
    kra_api_timeout: int = 30
    kra_api_max_retries: int = 3
    kra_rate_limit: int = 100  # requests per minute

    # Security
    secret_key: str = Field(
        default="dev-secret-key-change-in-production", env="SECRET_KEY"
    )  # Required from environment
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    api_key_header: str = "X-API-Key"

    # CORS
    allowed_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "https://app.kra-analysis.com",
    ]

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    log_file: str | None = "logs/api.log"

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

    # API Keys (loaded from environment)
    valid_api_keys: list[str] = Field(default_factory=list)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Load API keys from environment variable - REQUIRED in production
        api_keys_env = os.getenv("VALID_API_KEYS", "")
        if api_keys_env:
            # Try to parse as JSON array first
            try:
                import json

                self.valid_api_keys = json.loads(api_keys_env)
            except json.JSONDecodeError:
                # Fallback to comma-separated values
                self.valid_api_keys = [
                    key.strip() for key in api_keys_env.split(",") if key.strip()
                ]
        elif self.environment == "production":
            raise ValueError(
                "VALID_API_KEYS environment variable is required in production"
            )
        else:
            # Development/test mode - add a default test key
            self.valid_api_keys = ["test-api-key-123456789"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # 추가 필드 무시

        # 환경 변수 매핑
        fields = {
            "database_url": {"env": "DATABASE_URL"},
            "redis_url": {"env": "REDIS_URL"},
            "celery_broker_url": {"env": "CELERY_BROKER_URL"},
            "celery_result_backend": {"env": "CELERY_RESULT_BACKEND"},
            "kra_api_key": {"env": "KRA_API_KEY"},
            "secret_key": {"env": "SECRET_KEY"},
        }


@lru_cache
def get_settings() -> Settings:
    """설정 싱글톤 인스턴스 반환"""
    return Settings()


# 전역 설정 인스턴스
settings = get_settings()


# 환경별 설정 검증
if settings.environment == "production":
    # Ensure critical settings are configured
    if (
        not settings.secret_key
        or settings.secret_key == "your-secret-key-here-change-in-production"
    ):
        raise ValueError("SECRET_KEY must be set in production environment")
    if not settings.valid_api_keys:
        raise ValueError("VALID_API_KEYS must be set in production environment")


# Note: Directory creation has been moved to application startup
# See main_v2.py's lifespan function for directory creation

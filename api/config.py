from pydantic_settings import BaseSettings
from functools import lru_cache
import os
from typing import Optional


class Settings(BaseSettings):
    # Application
    app_name: str = "KRA Race Prediction API"
    version: str = "1.0.0"
    debug: bool = False
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    
    # Supabase
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_service_role_key: Optional[str] = None
    
    # KRA API
    kra_api_base_url: str = "http://apis.data.go.kr/B551015"
    kra_api_key: Optional[str] = None
    kra_api_timeout: int = 30
    kra_api_max_retries: int = 3
    kra_rate_limit: int = 100  # requests per minute
    
    # Redis Cache
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl: int = 3600  # 1 hour
    
    # Claude Code CLI
    claude_code_path: str = "claude-code"
    claude_prompt_mode: bool = True  # Use -p flag
    claude_timeout: int = 300  # 5 minutes for long operations
    
    # Security
    secret_key: str = "your-secret-key-here-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    # File Storage
    data_dir: str = "./data"
    cache_dir: str = "./data/cache"
    prompts_dir: str = "./prompts"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
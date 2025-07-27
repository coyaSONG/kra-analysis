from supabase import create_client, Client
from functools import lru_cache
from typing import Optional
from config import settings
import structlog


logger = structlog.get_logger()


@lru_cache()
def get_supabase_client() -> Optional[Client]:
    """
    Supabase 클라이언트 싱글톤 인스턴스를 반환합니다.
    Supabase가 설정되지 않은 경우 None을 반환합니다.
    """
    try:
        if not settings.supabase_url or settings.supabase_url == "your_supabase_url":
            logger.warning("Supabase is not configured. Running without database persistence.")
            return None
        
        if not settings.supabase_key or settings.supabase_key == "your_supabase_anon_key":
            logger.warning("Supabase key is not configured. Running without database persistence.")
            return None
        
        # 서비스 롤 키가 있으면 사용, 없으면 일반 키 사용
        key = settings.supabase_service_role_key if settings.supabase_service_role_key and settings.supabase_service_role_key != "your_service_role_key" else settings.supabase_key
        
        client = create_client(
            supabase_url=settings.supabase_url,
            supabase_key=key,
        )
        
        logger.info("Supabase client initialized successfully")
        return client
        
    except Exception as e:
        logger.error("Failed to initialize Supabase client", error=str(e))
        return None


async def initialize_database():
    """
    데이터베이스 테이블을 초기화합니다.
    Supabase 대시보드에서 수동으로 생성하는 것을 권장하지만,
    필요시 이 함수를 통해 자동화할 수 있습니다.
    """
    # 테이블 생성 SQL은 Supabase 대시보드에서 실행하는 것을 권장
    # 또는 migrations 폴더에 SQL 파일로 관리
    pass
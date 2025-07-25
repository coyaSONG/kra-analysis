"""
Redis 클라이언트 설정 및 관리
캐싱 및 Celery 브로커용
"""

import redis
from typing import Optional, Any
import json
import structlog
from contextlib import asynccontextmanager

from config import settings

logger = structlog.get_logger()

# Redis 클라이언트 인스턴스
redis_client: Optional[redis.Redis] = None


async def init_redis():
    """Redis 클라이언트 초기화"""
    global redis_client
    
    try:
        # Redis 5.0+ uses redis.asyncio.from_url
        from redis.asyncio import from_url
        
        redis_client = await from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            health_check_interval=30
        )
        
        # 연결 테스트
        await redis_client.ping()
        logger.info("Redis connected successfully", redis_url=settings.redis_url.split('@')[1] if '@' in settings.redis_url else 'local')
        
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise


async def close_redis():
    """Redis 연결 종료"""
    global redis_client
    
    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed")


def get_redis() -> redis.Redis:
    """Redis 클라이언트 반환"""
    if not redis_client:
        raise RuntimeError("Redis client not initialized")
    return redis_client


@asynccontextmanager
async def get_redis_session():
    """Redis 세션 컨텍스트 매니저"""
    client = get_redis()
    try:
        yield client
    except Exception as e:
        logger.error(f"Redis operation failed: {e}")
        raise


class CacheService:
    """캐시 서비스 클래스"""
    
    def __init__(self):
        self.client = None
        self.default_ttl = settings.cache_ttl
    
    def _ensure_client(self):
        """Ensure Redis client is initialized"""
        if not self.client:
            if redis_client:
                self.client = redis_client
            else:
                raise RuntimeError("Redis client not initialized. Call initialize() first.")
    
    async def initialize(self):
        """캐시 서비스 초기화"""
        self.client = get_redis()
    
    async def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 조회"""
        self._ensure_client()
        try:
            value = await self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning(f"Cache get failed for key {key}: {e}")
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None
    ) -> bool:
        """캐시에 값 저장"""
        self._ensure_client()
        try:
            ttl = ttl or self.default_ttl
            serialized = json.dumps(value, ensure_ascii=False)
            await self.client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.warning(f"Cache set failed for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """캐시에서 값 삭제"""
        self._ensure_client()
        try:
            result = await self.client.delete(key)
            return bool(result)
        except Exception as e:
            logger.warning(f"Cache delete failed for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """키 존재 여부 확인"""
        self._ensure_client()
        try:
            return bool(await self.client.exists(key))
        except Exception as e:
            logger.warning(f"Cache exists check failed for key {key}: {e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """패턴에 맞는 키 모두 삭제"""
        self._ensure_client()
        try:
            deleted_count = 0
            batch_size = 100  # Delete keys in batches to avoid memory issues
            batch = []
            
            async for key in self.client.scan_iter(match=pattern):
                batch.append(key)
                if len(batch) >= batch_size:
                    deleted_count += await self.client.delete(*batch)
                    batch = []
            
            # Delete remaining keys in the last batch
            if batch:
                deleted_count += await self.client.delete(*batch)
            
            return deleted_count
        except Exception as e:
            logger.warning(f"Cache clear pattern failed for {pattern}: {e}")
            return 0
    
    async def get_ttl(self, key: str) -> int:
        """키의 TTL 확인"""
        self._ensure_client()
        try:
            return await self.client.ttl(key)
        except Exception as e:
            logger.warning(f"Cache TTL check failed for key {key}: {e}")
            return -1


# 전역 캐시 서비스 인스턴스
cache_service = CacheService()


# 헬스체크용 함수
async def check_redis_connection():
    """Redis 연결 상태 확인"""
    try:
        if redis_client:
            await redis_client.ping()
            return True
        return False
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return False
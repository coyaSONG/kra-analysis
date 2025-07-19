"""
속도 제한 미들웨어
API 요청 속도 제한 구현
"""

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import time
import asyncio
from typing import Dict, Tuple
from collections import defaultdict
import structlog

from config import settings
from infrastructure.redis_client import get_redis

logger = structlog.get_logger()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """속도 제한 미들웨어"""
    
    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls  # 허용 요청 수
        self.period = period  # 기간 (초)
        # 메모리 기반 임시 저장 (Redis 사용 전)
        self.requests: Dict[str, list] = defaultdict(list)
        self.cleanup_interval = 300  # 5분마다 정리
        self.last_cleanup = time.time()
    
    async def dispatch(self, request: Request, call_next):
        # 속도 제한 활성화 확인
        if not settings.rate_limit_enabled:
            return await call_next(request)
        
        # 제외 경로 (헬스체크 등)
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # 클라이언트 식별 (API 키 또는 IP)
        client_id = self._get_client_id(request)
        
        # Redis 기반 속도 제한 (가능한 경우)
        try:
            redis_client = get_redis()
            if await self._check_rate_limit_redis(client_id, redis_client):
                return await call_next(request)
            else:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Maximum {self.calls} requests per {self.period} seconds."
                )
        except RuntimeError:
            # Redis 사용 불가 시 메모리 기반 폴백
            if self._check_rate_limit_memory(client_id):
                return await call_next(request)
            else:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Maximum {self.calls} requests per {self.period} seconds."
                )
    
    def _get_client_id(self, request: Request) -> str:
        """클라이언트 식별자 추출"""
        # API 키 우선
        api_key = request.headers.get("x-api-key")
        if api_key:
            return f"api_key:{api_key}"
        
        # IP 주소 폴백
        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"
    
    async def _check_rate_limit_redis(self, client_id: str, redis_client) -> bool:
        """Redis를 사용한 속도 제한 확인"""
        key = f"rate_limit:{client_id}"
        
        try:
            # 현재 시간
            now = time.time()
            
            # 파이프라인으로 원자적 실행
            pipe = redis_client.pipeline()
            pipe.zremrangebyscore(key, 0, now - self.period)  # 오래된 요청 제거
            pipe.zadd(key, {str(now): now})  # 현재 요청 추가
            pipe.zcount(key, now - self.period, now)  # 기간 내 요청 수 계산
            pipe.expire(key, self.period * 2)  # TTL 설정
            
            results = await pipe.execute()
            request_count = results[2]
            
            return request_count <= self.calls
            
        except Exception as e:
            logger.error(f"Redis rate limit check failed: {e}")
            return True  # 에러 시 통과
    
    def _check_rate_limit_memory(self, client_id: str) -> bool:
        """메모리 기반 속도 제한 확인"""
        now = time.time()
        
        # 주기적 정리
        if now - self.last_cleanup > self.cleanup_interval:
            self._cleanup_old_requests()
            self.last_cleanup = now
        
        # 현재 클라이언트의 요청 기록
        requests = self.requests[client_id]
        
        # 오래된 요청 제거
        requests = [req_time for req_time in requests if now - req_time < self.period]
        
        # 새 요청 추가
        requests.append(now)
        self.requests[client_id] = requests
        
        return len(requests) <= self.calls
    
    def _cleanup_old_requests(self):
        """오래된 요청 기록 정리"""
        now = time.time()
        for client_id in list(self.requests.keys()):
            self.requests[client_id] = [
                req_time for req_time in self.requests[client_id]
                if now - req_time < self.period
            ]
            if not self.requests[client_id]:
                del self.requests[client_id]


class APIKeyRateLimiter:
    """API 키별 세부 속도 제한"""
    
    def __init__(self):
        self.redis_client = None
    
    async def check_rate_limit(
        self, 
        api_key: str, 
        limit: int, 
        window: int = 60
    ) -> Tuple[bool, Dict[str, int]]:
        """
        API 키별 속도 제한 확인
        
        Returns:
            Tuple[bool, Dict]: (통과 여부, 상태 정보)
        """
        if not self.redis_client:
            try:
                self.redis_client = get_redis()
            except:
                return True, {"limit": limit, "remaining": limit, "reset": 0}
        
        key = f"api_rate:{api_key}:{int(time.time() // window)}"
        
        try:
            # 현재 카운트 증가
            current = await self.redis_client.incr(key)
            
            # 첫 요청인 경우 TTL 설정
            if current == 1:
                await self.redis_client.expire(key, window)
            
            # TTL 확인
            ttl = await self.redis_client.ttl(key)
            
            # 상태 정보
            info = {
                "limit": limit,
                "remaining": max(0, limit - current),
                "reset": int(time.time()) + ttl if ttl > 0 else int(time.time()) + window
            }
            
            return current <= limit, info
            
        except Exception as e:
            logger.error(f"API key rate limit check failed: {e}")
            return True, {"limit": limit, "remaining": limit, "reset": 0}
    
    def get_headers(self, info: Dict[str, int]) -> Dict[str, str]:
        """속도 제한 정보를 HTTP 헤더로 변환"""
        return {
            "X-RateLimit-Limit": str(info["limit"]),
            "X-RateLimit-Remaining": str(info["remaining"]),
            "X-RateLimit-Reset": str(info["reset"])
        }
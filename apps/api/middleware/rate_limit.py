"""
속도 제한 미들웨어
API 요청 속도 제한 구현
"""

import time

import structlog
from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware

from config import settings
from infrastructure.redis_client import get_redis

logger = structlog.get_logger()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """속도 제한 미들웨어"""

    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls  # 허용 요청 수
        self.period = period  # 기간 (초)
        self.redis_required = (
            settings.environment == "production"
        )  # 프로덕션에서는 Redis 필수

    async def dispatch(self, request: Request, call_next):
        # 테스트/개발 환경 또는 비활성화 시 즉시 통과
        try:
            if (settings.environment in {"test", "development"}) or (
                not settings.rate_limit_enabled
            ):
                return await call_next(request)
        except Exception:
            # 설정 조회 실패 시 안전하게 통과
            return await call_next(request)

        # 제외 경로 (헬스체크 등)
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        # 클라이언트 식별 (API 키 또는 IP)
        client_id = self._get_client_id(request)

        # Redis 기반 속도 제한
        try:
            redis_client = get_redis()
            # 파이프라인 인터페이스가 없으면(모킹 등) 레이트리밋을 우회
            if not hasattr(redis_client, "pipeline"):
                logger.warning("Redis client has no pipeline; bypassing rate limit")
                return await call_next(request)
            if await self._check_rate_limit_redis(client_id, redis_client):
                return await call_next(request)
            else:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Maximum {self.calls} requests per {self.period} seconds.",
                )
        except RuntimeError as e:
            # Redis 연결 실패
            if self.redis_required:
                logger.error("Redis required but not available", error=str(e))
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Rate limiting service unavailable",
                ) from e
            else:
                # 개발 환경에서만 통과 허용
                logger.warning(
                    "Redis not available, bypassing rate limit in development"
                )
                return await call_next(request)

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

    # In-memory rate limiting methods removed for horizontal scaling support


class APIKeyRateLimiter:
    """API 키별 세부 속도 제한"""

    def __init__(self):
        self.redis_client = None

    async def check_rate_limit(
        self, api_key: str, limit: int, window: int = 60
    ) -> tuple[bool, dict[str, int]]:
        """
        API 키별 속도 제한 확인

        Returns:
            Tuple[bool, Dict]: (통과 여부, 상태 정보)
        """
        if not self.redis_client:
            try:
                self.redis_client = get_redis()
            except Exception:
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
                "reset": (
                    int(time.time()) + ttl if ttl > 0 else int(time.time()) + window
                ),
            }

            return current <= limit, info

        except Exception as e:
            logger.error(f"API key rate limit check failed: {e}")
            return True, {"limit": limit, "remaining": limit, "reset": 0}

    def get_headers(self, info: dict[str, int]) -> dict[str, str]:
        """속도 제한 정보를 HTTP 헤더로 변환"""
        return {
            "X-RateLimit-Limit": str(info["limit"]),
            "X-RateLimit-Remaining": str(info["remaining"]),
            "X-RateLimit-Reset": str(info["reset"]),
        }

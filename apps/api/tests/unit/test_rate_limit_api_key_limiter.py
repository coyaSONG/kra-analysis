import pytest

from middleware.rate_limit import APIKeyRateLimiter
from tests.utils.mocks import MockRedisClient


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.asyncio
async def test_api_key_rate_limiter_counts_and_headers():
    limiter = APIKeyRateLimiter()
    limiter.redis_client = MockRedisClient()

    ok1, info1 = await limiter.check_rate_limit("key-1", limit=2, window=60)
    assert ok1 is True and info1["remaining"] == 1

    ok2, info2 = await limiter.check_rate_limit("key-1", limit=2, window=60)
    assert ok2 is True and info2["remaining"] == 0

    ok3, info3 = await limiter.check_rate_limit("key-1", limit=2, window=60)
    assert ok3 is False and info3["remaining"] == 0

    headers = limiter.get_headers(info2)
    assert (
        "X-RateLimit-Limit" in headers
        and "X-RateLimit-Remaining" in headers
        and "X-RateLimit-Reset" in headers
    )

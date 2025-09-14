"""
Unit tests for APIKeyRateLimiter utility in rate_limit middleware.
"""

import pytest

from middleware.rate_limit import APIKeyRateLimiter


class _DummyRedis:
    def __init__(self):
        self.store = {}
        self.expiries = {}

    async def incr(self, key):
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    async def expire(self, key, window):
        self.expiries[key] = window
        return True

    async def ttl(self, key):
        # return a positive TTL if set, else default to 60
        return self.expiries.get(key, 60)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_api_key_rate_limiter_allows_then_blocks():
    limiter = APIKeyRateLimiter()
    limiter.redis_client = _DummyRedis()

    ok, info1 = await limiter.check_rate_limit("k1", limit=2, window=60)
    assert ok is True and info1["remaining"] in (1, 2)

    ok, info2 = await limiter.check_rate_limit("k1", limit=2, window=60)
    assert ok is True and info2["remaining"] in (0, 1)

    # Third should block
    ok, info3 = await limiter.check_rate_limit("k1", limit=2, window=60)
    assert ok is False and info3["remaining"] == 0

    headers = limiter.get_headers(info3)
    assert set(["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"]).issubset(headers.keys())


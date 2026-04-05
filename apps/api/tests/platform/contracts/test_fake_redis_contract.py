import pytest

from tests.platform.fakes import FakeRedis


@pytest.mark.asyncio
async def test_fake_redis_supports_cache_contract():
    redis = FakeRedis()

    await redis.setex("cache:race:1", 60, '{"ok": true}')
    assert await redis.get("cache:race:1") == '{"ok": true}'
    assert await redis.exists("cache:race:1") == 1
    assert await redis.ttl("cache:race:1") >= 0

    keys = [key async for key in redis.scan_iter(match="cache:*")]
    assert keys == ["cache:race:1"]


@pytest.mark.asyncio
async def test_fake_redis_supports_rate_limit_pipeline_contract():
    redis = FakeRedis()
    pipe = redis.pipeline()
    pipe.zremrangebyscore("rate_limit:key1", 0, 10)
    pipe.zadd("rate_limit:key1", {"100.0": 100.0})
    pipe.zcount("rate_limit:key1", 40, 100)
    pipe.expire("rate_limit:key1", 120)

    results = await pipe.execute()

    assert results[2] == 1
    assert await redis.ttl("rate_limit:key1") >= 0

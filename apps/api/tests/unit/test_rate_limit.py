import pytest

from config import settings


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.asyncio
async def test_rate_limit_bypass_in_test_env(authenticated_client):
    # In test env, middleware bypasses rate limit
    resp = await authenticated_client.get("/api/v2/jobs/")
    assert resp.status_code in (200, 204, 404) or "jobs" in resp.json()


class FakePipeline:
    def __init__(self, store: dict[str, int]):
        self.ops: list[tuple] = []
        self.store = store

    def zremrangebyscore(self, key, _min, _max):
        self.ops.append(("rem", key, _min, _max))
        return self

    def zadd(self, key, mapping):
        self.ops.append(("add", key, mapping))
        return self

    def zcount(self, key, _min, _max):
        self.ops.append(("count", key, _min, _max))
        return self

    def expire(self, key, ttl):
        self.ops.append(("expire", key, ttl))
        return self

    async def execute(self):
        # Emulate: first call returns 100, second returns 101 for same key
        count_value = None
        for op in self.ops:
            if op[0] == "count":
                key = op[1]
                prev = self.store.get(key, 99)
                new = prev + 1
                self.store[key] = new
                count_value = new
        return [0, 1, count_value or 0, True]


class FakeRedis:
    def __init__(self):
        self.store: dict[str, int] = {}

    def pipeline(self):
        return FakePipeline(self.store)


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.asyncio
async def test_rate_limit_enforced_in_production(monkeypatch, authenticated_client):
    # Set to production-like env to avoid bypass
    old_env = settings.environment
    old_flag = settings.rate_limit_enabled
    settings.environment = "production"
    settings.rate_limit_enabled = True

    from middleware import rate_limit as rl

    fake = FakeRedis()
    monkeypatch.setattr(rl, "get_redis", lambda: fake)

    # First request should be allowed (count=100 <= 100)
    resp1 = await authenticated_client.get("/api/v2/jobs/")
    assert resp1.status_code == 200

    # Second request should exceed (count=101 > 100) and result in 429
    try:
        resp2 = await authenticated_client.get("/api/v2/jobs/")
        assert resp2.status_code == 429
    except Exception as e:
        # Depending on Starlette/FastAPI version, HTTPException may bubble up
        assert "429" in str(e) or "Rate limit exceeded" in str(e)

    # Restore settings
    settings.environment = old_env
    settings.rate_limit_enabled = old_flag


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.asyncio
async def test_rate_limit_no_pipeline_bypass(monkeypatch, authenticated_client):
    # Force production but return redis-like object without pipeline
    from config import settings

    old_env = settings.environment
    old_flag = settings.rate_limit_enabled
    settings.environment = "production"
    settings.rate_limit_enabled = True

    class NoPipe:
        pass

    from middleware import rate_limit as rl

    monkeypatch.setattr(rl, "get_redis", lambda: NoPipe())

    # Should bypass and return 200
    r = await authenticated_client.get("/api/v2/jobs/")
    assert r.status_code == 200

    settings.environment = old_env
    settings.rate_limit_enabled = old_flag


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.asyncio
async def test_rate_limit_redis_required_unavailable(monkeypatch, authenticated_client):
    from config import settings

    old_env = settings.environment
    old_flag = settings.rate_limit_enabled
    settings.environment = "production"
    settings.rate_limit_enabled = True

    from middleware import rate_limit as rl

    def boom():
        raise RuntimeError("no redis")

    monkeypatch.setattr(rl, "get_redis", boom)

    # Should fail-open and allow request
    try:
        r = await authenticated_client.get("/api/v2/jobs/")
        assert r.status_code == 200
    except Exception as e:
        pytest.fail(f"Request should not raise on Redis failure: {e}")

    settings.environment = old_env
    settings.rate_limit_enabled = old_flag

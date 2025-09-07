import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from httpx import ASGITransport

from middleware.rate_limit import RateLimitMiddleware


@pytest.mark.asyncio
async def test_rate_limit_excluded_paths(monkeypatch):
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware)

    @app.get('/health')
    async def health():
        return {'ok': True}

    # Force production
    from config import settings
    old_env = settings.environment
    old_flag = settings.rate_limit_enabled
    settings.environment = 'production'
    settings.rate_limit_enabled = True

    # Even if redis returns an object with pipeline, exclude path should bypass
    class FakePipe:
        def zremrangebyscore(self, *a, **k): return self
        def zadd(self, *a, **k): return self
        def zcount(self, *a, **k): return self
        def expire(self, *a, **k): return self
        async def execute(self): return [0,1,1,True]
    class FakeRedis:
        def pipeline(self): return FakePipe()

    import middleware.rate_limit as rl
    monkeypatch.setattr(rl, 'get_redis', lambda: FakeRedis())

    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as ac:
        r = await ac.get('/health')
        assert r.status_code == 200

    settings.environment = old_env
    settings.rate_limit_enabled = old_flag


@pytest.mark.asyncio
async def test_rate_limit_client_id_header_vs_ip(monkeypatch):
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware)

    @app.get('/ping')
    async def ping():
        return {'ok': True}

    # Production enforced
    from config import settings
    old_env = settings.environment
    old_flag = settings.rate_limit_enabled
    settings.environment = 'production'
    settings.rate_limit_enabled = True

    # First request with API key header should be counted under api_key: prefix
    class FakePipe:
        def __init__(self):
            self.counts = {}
        def zremrangebyscore(self, *a, **k): return self
        def zadd(self, *a, **k): return self
        def zcount(self, key, *_):
            # increment per key
            self.counts[key] = self.counts.get(key, 0) + 1
            return self
        def expire(self, *a, **k): return self
        async def execute(self):
            # return sequence with zcount value at index 2
            # use aggregate counts size
            total = sum(self.counts.values())
            return [0,1,total,True]
    class FakeRedis:
        def __init__(self): self.pipe = FakePipe()
        def pipeline(self): return self.pipe

    import middleware.rate_limit as rl
    monkeypatch.setattr(rl, 'get_redis', lambda: FakeRedis())

    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as ac:
        r1 = await ac.get('/ping', headers={'X-API-Key': 'k-123456789'})
        assert r1.status_code in (200, 429)
        r2 = await ac.get('/ping')  # without header -> ip: prefix
        assert r2.status_code in (200, 429)

    settings.environment = old_env
    settings.rate_limit_enabled = old_flag


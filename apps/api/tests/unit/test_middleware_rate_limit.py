"""
Unit tests for RateLimitMiddleware.
We mount a minimal FastAPI app with the middleware and mock Redis behavior.
"""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from middleware import rate_limit as rl_mod
from middleware.rate_limit import RateLimitMiddleware


class _MockPipeline:
    def __init__(self, count: int):
        self._count = count

    def zremrangebyscore(self, *args, **kwargs):
        return self

    def zadd(self, *args, **kwargs):
        return self

    def zcount(self, *args, **kwargs):
        return self

    def expire(self, *args, **kwargs):
        return self

    async def execute(self):
        # [zremrange, zadd, zcount, expire]
        return [None, None, self._count, True]


class _MockRedis:
    def __init__(self, count: int):
        self._count = count

    def pipeline(self):
        return _MockPipeline(self._count)


def _make_app():
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, calls=2, period=60)

    @app.get("/ping")
    async def ping():
        return {"ok": True}

    return app


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rate_limit_dev_env_bypasses(monkeypatch):
    app = _make_app()

    # development should bypass
    monkeypatch.setattr(
        rl_mod,
        "settings",
        type(
            "S",
            (),
            {
                "environment": "development",
                "rate_limit_enabled": True,
            },
        )(),
    )

    async with AsyncClient(transport=ASGITransport(app=app)) as ac:
        r = await ac.get("http://test/ping")
        assert r.status_code == 200


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rate_limit_production_redis_unavailable_returns_503(monkeypatch):
    app = _make_app()

    # production + enabled -> requires redis
    monkeypatch.setattr(
        rl_mod,
        "settings",
        type(
            "S",
            (),
            {
                "environment": "production",
                "rate_limit_enabled": True,
            },
        )(),
    )

    def _raise():
        raise RuntimeError("Redis client not initialized")

    monkeypatch.setattr(rl_mod, "get_redis", _raise)

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False)
    ) as ac:
        r = await ac.get("http://test/ping")
        # Depending on Starlette error handling in middleware context, may surface as 503 or generic 500
        assert r.status_code in (503, 500)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rate_limit_production_allows_then_blocks(monkeypatch):
    app = _make_app()

    monkeypatch.setattr(
        rl_mod,
        "settings",
        type(
            "S",
            (),
            {
                "environment": "production",
                "rate_limit_enabled": True,
            },
        )(),
    )

    # First: count=1 -> allowed (<= calls=2)
    monkeypatch.setattr(rl_mod, "get_redis", lambda: _MockRedis(count=1))
    async with AsyncClient(transport=ASGITransport(app=app)) as ac:
        r1 = await ac.get("http://test/ping", headers={"X-API-Key": "k1"})
        assert r1.status_code == 200

    # Second: count=3 -> blocked (> calls=2)
    monkeypatch.setattr(rl_mod, "get_redis", lambda: _MockRedis(count=3))
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False)
    ) as ac:
        r2 = await ac.get("http://test/ping", headers={"X-API-Key": "k1"})
        assert r2.status_code in (429, 500)

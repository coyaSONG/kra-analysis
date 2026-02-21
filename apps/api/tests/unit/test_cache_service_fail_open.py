import pytest

import infrastructure.redis_client as redis_module
from infrastructure.redis_client import CacheService


@pytest.mark.asyncio
@pytest.mark.unit
async def test_cache_service_get_without_redis_returns_none(monkeypatch):
    monkeypatch.setattr(redis_module, "redis_client", None)
    cache = CacheService()

    value = await cache.get("missing")
    assert value is None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_cache_service_set_without_redis_returns_false(monkeypatch):
    monkeypatch.setattr(redis_module, "redis_client", None)
    cache = CacheService()

    ok = await cache.set("k", {"v": 1})
    assert ok is False

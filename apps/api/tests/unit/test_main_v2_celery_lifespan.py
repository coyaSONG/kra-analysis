import pytest
from httpx import AsyncClient
from httpx import ASGITransport

import main_v2


class DummyInspect:
    def active(self):
        return {'worker1': []}


class DummyControl:
    def inspect(self):
        return DummyInspect()


class DummyCelery:
    def __init__(self):
        self.control = DummyControl()


@pytest.mark.asyncio
async def test_lifespan_with_celery_inspect(monkeypatch):
    # Patch celery_app used in main_v2
    monkeypatch.setattr(main_v2, 'celery_app', DummyCelery())
    transport = ASGITransport(app=main_v2.app)
    async with AsyncClient(transport=transport, base_url='http://test') as ac:
        r = await ac.get('/health')
        assert r.status_code == 200


class BoomInspect:
    def active(self):
        raise RuntimeError('boom')


class BoomControl:
    def inspect(self):
        return BoomInspect()


@pytest.mark.asyncio
async def test_lifespan_with_celery_inspect_error(monkeypatch):
    monkeypatch.setattr(main_v2, 'celery_app', type('X', (), {'control': BoomControl()})())
    transport = ASGITransport(app=main_v2.app)
    async with AsyncClient(transport=transport, base_url='http://test') as ac:
        r = await ac.get('/health')
        assert r.status_code == 200


@pytest.mark.asyncio
async def test_lifespan_redis_init_fail(monkeypatch):
    import infrastructure.redis_client as rc
    async def boom():
        raise RuntimeError('redis down')
    monkeypatch.setattr(rc, 'init_redis', boom)

    transport = ASGITransport(app=main_v2.app)
    async with AsyncClient(transport=transport, base_url='http://test') as ac:
        r = await ac.get('/health')
        assert r.status_code == 200

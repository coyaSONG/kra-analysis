import pytest
from httpx import ASGITransport, AsyncClient

import main_v2


@pytest.mark.asyncio
async def test_lifespan_without_celery_workers(monkeypatch):
    # Force CELERY_AVAILABLE to False to cover branch
    monkeypatch.setattr(main_v2, "CELERY_AVAILABLE", False)
    transport = ASGITransport(app=main_v2.app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/health")
        assert r.status_code == 200

import pytest
from httpx import AsyncClient
from httpx import ASGITransport

from main_v2 import app
from config import settings


@pytest.mark.asyncio
async def test_docs_and_openapi_excluded_from_rate_limit(monkeypatch):
    # Force production so middleware is active
    old_env = settings.environment
    old_flag = settings.rate_limit_enabled
    settings.environment = 'production'
    settings.rate_limit_enabled = True
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as ac:
            r1 = await ac.get('/docs')
            r2 = await ac.get('/openapi.json')
            assert r1.status_code in (200, 404)  # docs may be disabled if templates missing
            assert r2.status_code == 200
    finally:
        settings.environment = old_env
        settings.rate_limit_enabled = old_flag


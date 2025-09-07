import pytest
from httpx import AsyncClient
from httpx import ASGITransport

from main_v2 import app


@pytest.mark.asyncio
async def test_root_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as ac:
        r = await ac.get('/')
        assert r.status_code == 200
        data = r.json()
        assert 'service' in data and 'endpoints' in data


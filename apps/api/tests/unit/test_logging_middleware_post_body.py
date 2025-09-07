import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from httpx import ASGITransport

from middleware.logging import LoggingMiddleware


@pytest.mark.asyncio
async def test_logging_middleware_logs_body():
    app = FastAPI()
    app.add_middleware(LoggingMiddleware)

    @app.post('/echo')
    async def echo(item: dict):
        return item

    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as ac:
        r = await ac.post('/echo', json={'a': 1})
        assert r.status_code == 200
        assert r.json() == {'a': 1}


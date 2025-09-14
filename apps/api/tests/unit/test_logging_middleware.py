import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from middleware.logging import LoggingMiddleware


@pytest.mark.asyncio
async def test_logging_middleware_sets_request_id():
    app = FastAPI()
    app.add_middleware(LoggingMiddleware)

    @app.get("/ping")
    async def ping():
        return {"ok": True}

    from httpx import ASGITransport

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        r = await ac.get("/ping")
        assert r.status_code == 200
        assert "X-Request-ID" in r.headers

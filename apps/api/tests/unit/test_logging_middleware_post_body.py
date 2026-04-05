import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from middleware.logging import RequestLoggingMiddleware


@pytest.mark.asyncio
@pytest.mark.unit
async def test_request_logging_preserves_request_body_for_downstream_handlers():
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.post("/echo")
    async def echo(item: dict):
        return item

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post("/echo", json={"a": 1})

    assert response.status_code == 200
    assert response.json() == {"a": 1}

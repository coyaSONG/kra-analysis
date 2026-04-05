import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from middleware import logging as logging_middleware
from middleware.logging import RequestLoggingMiddleware


@pytest.mark.asyncio
@pytest.mark.unit
async def test_request_logging_error_path_logs_request_failed(monkeypatch):
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    errors = []

    def fake_error(event, **kwargs):
        errors.append((event, kwargs))

    monkeypatch.setattr(logging_middleware.logger, "error", fake_error)

    @app.get("/err")
    async def err():
        raise RuntimeError("boom")

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as ac:
        response = await ac.get("/err")

    assert response.status_code == 500
    failed = next(kwargs for event, kwargs in errors if event == "request_failed")
    assert failed["path"] == "/err"
    assert failed["method"] == "GET"
    assert failed["error"] == "boom"

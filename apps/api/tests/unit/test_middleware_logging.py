"""
Unit tests for LoggingMiddleware.
"""

import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from middleware.logging import LoggingMiddleware


def _make_app():
    app = FastAPI()
    app.add_middleware(LoggingMiddleware)

    @app.get("/ok")
    async def ok():
        return {"ok": True}

    @app.get("/boom")
    async def boom():
        raise RuntimeError("boom")

    return app


@pytest.mark.unit
@pytest.mark.asyncio
async def test_logging_middleware_adds_request_id_header():
    app = _make_app()
    async with AsyncClient(transport=ASGITransport(app=app)) as ac:
        r = await ac.get("http://test/ok")
        assert r.status_code == 200
        assert r.headers.get("X-Request-ID")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_logging_middleware_error_path_returns_500():
    app = _make_app()
    # Do not raise app exceptions to let middleware log and return 500
    async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False)) as ac:
        r = await ac.get("http://test/boom")
        assert r.status_code == 500


import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient

from middleware import logging as logging_middleware
from middleware.logging import RequestLoggingMiddleware


def _make_app():
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/ok")
    async def ok(request: Request):
        return {
            "ok": True,
            "request_id": getattr(request.state, "request_id", None),
        }

    @app.get("/boom")
    async def boom():
        raise RuntimeError("boom")

    return app


@pytest.mark.unit
@pytest.mark.asyncio
async def test_request_logging_middleware_adds_request_id_header_and_state():
    app = _make_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/ok")

    assert response.status_code == 200
    request_id = response.headers.get("X-Request-ID")
    assert request_id
    assert response.json()["request_id"] == request_id


@pytest.mark.unit
@pytest.mark.asyncio
async def test_request_logging_middleware_emits_started_and_completed_events(
    monkeypatch,
):
    app = _make_app()
    captured: list[tuple[str, dict]] = []

    def fake_info(event, **kwargs):
        captured.append((event, kwargs))

    monkeypatch.setattr(logging_middleware.logger, "info", fake_info)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/ok")

    assert response.status_code == 200
    started = next(kwargs for event, kwargs in captured if event == "request_started")
    completed = next(
        kwargs for event, kwargs in captured if event == "request_completed"
    )
    assert started["request_id"] == completed["request_id"]
    assert started["path"] == "/ok"
    assert completed["status_code"] == 200
    assert completed["error"] is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_request_logging_middleware_error_path_logs_failure(monkeypatch):
    app = _make_app()
    errors: list[tuple[str, dict]] = []

    def fake_error(event, **kwargs):
        errors.append((event, kwargs))

    monkeypatch.setattr(logging_middleware.logger, "error", fake_error)

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as ac:
        response = await ac.get("/boom")

    assert response.status_code == 500
    failed = next(kwargs for event, kwargs in errors if event == "request_failed")
    assert failed["path"] == "/boom"
    assert failed["method"] == "GET"
    assert failed["request_id"]

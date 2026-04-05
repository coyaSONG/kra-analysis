import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from middleware import logging as logging_middleware
from middleware.logging import RequestLoggingMiddleware


@pytest.mark.unit
def test_mask_sensitive_fields_redacts_only_sensitive_keys():
    masked = logging_middleware._mask_sensitive_fields(
        {
            "api_key": "abcd12345678",
            "authorization": "Bearer super-secret-token",
            "serviceKey": "svc123456",
            "page": "1",
            "user-agent": "test-client",
        }
    )

    assert masked["api_key"] == "abcd***"
    assert masked["authorization"] == "Bear***"
    assert masked["serviceKey"] == "svc1***"
    assert masked["page"] == "1"
    assert masked["user-agent"] == "test-client"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_request_logging_masks_sensitive_headers_and_query_params(monkeypatch):
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    captured = []

    def fake_info(event, **kwargs):
        captured.append((event, kwargs))

    monkeypatch.setattr(logging_middleware.logger, "info", fake_info)

    @app.get("/items")
    async def items():
        return {"ok": True}

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get(
            "/items?serviceKey=abcd123456&page=2",
            headers={
                "Authorization": "Bearer top-secret-token",
                "X-API-Key": "key123456789",
                "X-Request-Source": "dashboard",
                "User-Agent": "test-client",
            },
        )

    assert response.status_code == 200

    request_started = next(
        kwargs for event, kwargs in captured if event == "request_started"
    )

    assert request_started["query_params"]["serviceKey"] == "abcd***"
    assert request_started["query_params"]["page"] == "2"
    assert request_started["headers"]["authorization"] == "Bear***"
    assert request_started["headers"]["x-api-key"] == "key1***"
    assert request_started["headers"]["x-request-source"] == "dashboard"
    assert request_started["user_agent"] == "test-client"
    assert request_started["has_api_key"] is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_request_logging_masks_small_json_body(monkeypatch):
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    debug_events = []

    def fake_debug(event, **kwargs):
        debug_events.append((event, kwargs))

    monkeypatch.setattr(logging_middleware.logger, "debug", fake_debug)

    @app.post("/echo")
    async def echo(item: dict):
        return item

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/echo",
            json={
                "api_key": "secret-12345",
                "authorization": "Bearer top-secret-token",
                "page": 1,
            },
        )

    assert response.status_code == 200
    request_body = next(
        kwargs for event, kwargs in debug_events if event == "request_body"
    )
    assert request_body["body"]["api_key"] == "secr***"
    assert request_body["body"]["authorization"] == "Bear***"
    assert request_body["body"]["page"] == 1

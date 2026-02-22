import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from starlette.requests import Request as StarletteRequest

import middleware.logging as logging_module
from middleware.logging import RequestLoggingMiddleware


class _CaptureLogger:
    def __init__(self):
        self.debug_calls = []

    def debug(self, event, **kwargs):
        self.debug_calls.append((event, kwargs))


@pytest.mark.unit
@pytest.mark.asyncio
async def test_request_body_redacts_sensitive_top_level_keys(monkeypatch):
    capture = _CaptureLogger()
    monkeypatch.setattr(logging_module, "logger", capture)

    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.post("/echo")
    async def echo(item: dict):
        return item

    payload = {
        "api_key": "plain-key",
        "x-api-key": "x-key",
        "authorization": "Bearer abc",
        "token": "tok",
        "secret": "sec",
        "serviceKey": "svc",
        "service_key": "svc2",
        "password": "pw",
        "normal": "ok",
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post("/echo", json=payload)

    assert response.status_code == 200

    request_body_logs = [
        call for call in capture.debug_calls if call[0] == "request_body"
    ]
    assert request_body_logs

    body = request_body_logs[0][1]["body"]
    assert body["api_key"] == "[REDACTED]"
    assert body["x-api-key"] == "[REDACTED]"
    assert body["authorization"] == "[REDACTED]"
    assert body["token"] == "[REDACTED]"
    assert body["secret"] == "[REDACTED]"
    assert body["serviceKey"] == "[REDACTED]"
    assert body["service_key"] == "[REDACTED]"
    assert body["password"] == "[REDACTED]"
    assert body["normal"] == "ok"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_request_body_redacts_sensitive_keys_in_nested_structures(monkeypatch):
    capture = _CaptureLogger()
    monkeypatch.setattr(logging_module, "logger", capture)

    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.post("/echo")
    async def echo(item: dict):
        return item

    payload = {
        "outer": {
            "Token": "tok-1",
            "child": [{"password": "pw-1"}, {"safe": "value"}],
        },
        "items": [
            {"Authorization": "Bearer nested"},
            {"servicekey": "nested-service-key"},
            {"deep": {"SeCrEt": "hidden"}},
        ],
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post("/echo", json=payload)

    assert response.status_code == 200

    request_body_logs = [
        call for call in capture.debug_calls if call[0] == "request_body"
    ]
    assert request_body_logs

    body = request_body_logs[0][1]["body"]
    assert body["outer"]["Token"] == "[REDACTED]"
    assert body["outer"]["child"][0]["password"] == "[REDACTED]"
    assert body["outer"]["child"][1]["safe"] == "value"
    assert body["items"][0]["Authorization"] == "[REDACTED]"
    assert body["items"][1]["servicekey"] == "[REDACTED]"
    assert body["items"][2]["deep"]["SeCrEt"] == "[REDACTED]"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_request_body_over_10kb_is_not_logged_as_full_body(monkeypatch):
    capture = _CaptureLogger()
    monkeypatch.setattr(logging_module, "logger", capture)

    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.post("/echo")
    async def echo(item: dict):
        return {"ok": True}

    payload = {
        "huge": "x" * 11000,
        "token": "should-not-appear-when-too-large",
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post("/echo", json=payload)

    assert response.status_code == 200

    events = [event for event, _ in capture.debug_calls]
    assert "request_body" not in events

    for event, kwargs in capture.debug_calls:
        assert event == "request_body_raw"
        assert "body_length" in kwargs


@pytest.mark.unit
@pytest.mark.asyncio
async def test_large_content_length_does_not_call_request_body(monkeypatch):
    capture = _CaptureLogger()
    monkeypatch.setattr(logging_module, "logger", capture)

    body_call_count = 0
    original_body = StarletteRequest.body

    async def counting_body(self):
        nonlocal body_call_count
        body_call_count += 1
        return await original_body(self)

    monkeypatch.setattr(StarletteRequest, "body", counting_body)

    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.post("/skip-body-read")
    async def skip_body_read():
        return {"ok": True}

    payload = "x" * (10 * 1024)
    headers = {"content-type": "text/plain", "content-length": str(10 * 1024)}

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post("/skip-body-read", content=payload, headers=headers)

    assert response.status_code == 200
    assert body_call_count == 0

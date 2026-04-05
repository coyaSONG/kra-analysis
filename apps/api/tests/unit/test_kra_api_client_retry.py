import json
from unittest.mock import AsyncMock

import httpx
import pytest

from infrastructure.kra_api import client as kra_client_module
from infrastructure.kra_api import core as kra_core


def _make_response(
    status_code: int,
    payload: dict | None = None,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    request = httpx.Request("GET", "https://example.test/kra")
    return httpx.Response(
        status_code,
        request=request,
        headers=headers,
        content=json.dumps(payload or {}).encode(),
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_make_request_retries_429_with_retry_after(monkeypatch):
    responses = [
        _make_response(429, {"error": "rate limited"}, headers={"Retry-After": "7"}),
        _make_response(200, {"response": {"header": {"resultCode": "00"}}}),
    ]
    sleep = AsyncMock()
    call_count = {"value": 0}

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def request(self, method, url, params=None, json=None):
            response = responses[call_count["value"]]
            call_count["value"] += 1
            return response

    monkeypatch.setattr(kra_client_module.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(kra_core.asyncio, "sleep", sleep)
    monkeypatch.setattr(kra_client_module.settings, "kra_api_key", "test-api-key")
    monkeypatch.setattr(kra_client_module.settings, "kra_api_max_retries", 2)

    client = kra_client_module.KRAApiClient()
    result = await client._make_request("/retry-429", {})

    assert result["response"]["header"]["resultCode"] == "00"
    assert call_count["value"] == 2
    sleep.assert_awaited_once_with(7.0)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_make_request_raises_auth_error_without_retry_on_401(monkeypatch):
    sleep = AsyncMock()
    call_count = {"value": 0}

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def request(self, method, url, params=None, json=None):
            call_count["value"] += 1
            return _make_response(401, {"error": "unauthorized"})

    monkeypatch.setattr(kra_client_module.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(kra_core.asyncio, "sleep", sleep)
    monkeypatch.setattr(kra_client_module.settings, "kra_api_key", "test-api-key")
    monkeypatch.setattr(kra_client_module.settings, "kra_api_max_retries", 3)

    client = kra_client_module.KRAApiClient()

    with pytest.raises(kra_client_module.KRAApiAuthenticationError):
        await client._make_request("/auth-error", {})

    assert call_count["value"] == 1
    sleep.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_make_request_retries_5xx_with_exponential_backoff(monkeypatch):
    responses = [
        _make_response(503, {"error": "temporary failure"}),
        _make_response(502, {"error": "temporary failure"}),
        _make_response(200, {"response": {"header": {"resultCode": "00"}}}),
    ]
    sleep = AsyncMock()
    call_count = {"value": 0}

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def request(self, method, url, params=None, json=None):
            response = responses[call_count["value"]]
            call_count["value"] += 1
            return response

    monkeypatch.setattr(kra_client_module.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(kra_core.asyncio, "sleep", sleep)
    monkeypatch.setattr(kra_client_module.settings, "kra_api_key", "test-api-key")
    monkeypatch.setattr(kra_client_module.settings, "kra_api_max_retries", 3)

    client = kra_client_module.KRAApiClient()
    result = await client._make_request("/server-error", {})

    assert result["response"]["header"]["resultCode"] == "00"
    assert call_count["value"] == 3
    assert sleep.await_args_list[0].args == (1.0,)
    assert sleep.await_args_list[1].args == (2.0,)

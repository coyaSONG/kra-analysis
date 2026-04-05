import json
from unittest.mock import AsyncMock

import httpx
import pytest

from config import Settings
from infrastructure.kra_api.core import (
    KRARequestPolicy,
    build_httpx_client_kwargs,
    build_request_params,
    cache_ttl_for,
    request_json_with_retry,
)


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


def test_build_request_params_decodes_key_and_sets_json_type():
    params = {"meet": "1"}

    result = build_request_params(params, "test%2Bkey")

    assert result["serviceKey"] == "test+key"
    assert result["_type"] == "json"
    assert params == {"meet": "1"}


def test_cache_ttl_for_known_namespaces():
    assert cache_ttl_for("race_info") == 3600
    assert cache_ttl_for("cancelled_horses") == 1800


def test_build_httpx_client_kwargs_uses_ssl_and_user_agent():
    policy = KRARequestPolicy(
        base_url="https://example.test",
        api_key="abc",
        timeout=12,
        max_retries=3,
        verify_ssl=False,
        user_agent="kra-analysis/1.0",
    )

    kwargs = build_httpx_client_kwargs(policy)

    assert kwargs["verify"] is False
    assert kwargs["timeout"].connect == 12
    assert kwargs["timeout"].read == 12
    assert kwargs["headers"]["Accept"] == "application/json"
    assert kwargs["headers"]["User-Agent"] == "kra-analysis/1.0"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_request_json_with_retry_retries_429_with_retry_after(monkeypatch):
    responses = [
        _make_response(429, {"error": "rate limited"}, headers={"Retry-After": "7"}),
        _make_response(200, {"response": {"header": {"resultCode": "00"}}}),
    ]
    sleep = AsyncMock()
    call_count = {"value": 0}

    class FakeAsyncClient:
        async def request(self, method, url, params, json=None):
            response = responses[call_count["value"]]
            call_count["value"] += 1
            return response

    monkeypatch.setattr("infrastructure.kra_api.core.asyncio.sleep", sleep)

    policy = KRARequestPolicy(
        base_url="https://example.test",
        api_key="test-api-key",
        timeout=30,
        max_retries=2,
        verify_ssl=True,
    )

    result = await request_json_with_retry(
        FakeAsyncClient(), policy, "/retry-429", params={}
    )

    assert result["response"]["header"]["resultCode"] == "00"
    assert call_count["value"] == 2
    sleep.assert_awaited_once_with(7.0)


@pytest.mark.unit
def test_settings_disallow_disabling_kra_ssl_outside_development(monkeypatch):
    monkeypatch.setenv("VALID_API_KEYS", '["prod-key-1234567890"]')

    with pytest.raises(
        ValueError,
        match="KRA_API_VERIFY_SSL can only be disabled in development environment",
    ):
        Settings(
            environment="production",
            kra_api_verify_ssl=False,
        )

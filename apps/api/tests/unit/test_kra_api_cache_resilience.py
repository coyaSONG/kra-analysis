import httpx
import pytest

from infrastructure.kra_api import core as kra_core
from services import kra_api_service as kra_api_service_module
from services.kra_api_service import KRAAPIService


class FailingCache:
    async def get(self, key):
        raise RuntimeError("redis read failed")

    async def set(self, key, value, ttl=None):
        return True


class HealthyCache:
    async def get(self, key):
        return None

    async def set(self, key, value, ttl=None):
        return True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cache_failure_streak_escalates_to_error(monkeypatch):
    service = KRAAPIService()
    service._cache_service = FailingCache()
    kra_api_service_module._cache_failure_streak = 0
    warning_calls = []
    error_calls = []

    monkeypatch.setattr(
        kra_api_service_module.logger,
        "warning",
        lambda event, **kwargs: warning_calls.append((event, kwargs)),
    )
    monkeypatch.setattr(
        kra_api_service_module.logger,
        "error",
        lambda event, **kwargs: error_calls.append((event, kwargs)),
    )

    for _ in range(4):
        assert await service._get_cached("race_info:test") is None

    assert len(warning_calls) == 4
    assert all(
        call[1]["failure_count"] == idx
        for idx, call in enumerate(warning_calls, start=1)
    )

    assert await service._get_cached("race_info:test") is None

    assert len(error_calls) == 1
    assert error_calls[0][1]["failure_count"] == 5


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cache_failure_streak_resets_after_success():
    service = KRAAPIService()
    kra_api_service_module._cache_failure_streak = 3
    service._cache_service = HealthyCache()

    assert await service._get_cached("race_info:test") is None
    assert kra_api_service_module._cache_failure_streak == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_make_request_logs_rate_limit_headers(monkeypatch):
    service = KRAAPIService()
    info_calls = []

    request = httpx.Request("GET", "https://example.test/API214_1/RaceDetailResult_1")
    response = httpx.Response(
        200,
        request=request,
        headers={
            "X-RateLimit-Limit": "100",
            "X-RateLimit-Remaining": "42",
            "X-RateLimit-Reset": "1700000000",
        },
        json={"response": {"header": {"resultCode": "00"}}},
    )

    async def fake_request(method, url, params=None, json=None):
        return response

    monkeypatch.setattr(service.client, "request", fake_request)
    monkeypatch.setattr(
        kra_core.logger,
        "info",
        lambda event, **kwargs: info_calls.append((event, kwargs)),
    )

    result = await service._make_request("API214_1/RaceDetailResult_1", params={})

    assert result["response"]["header"]["resultCode"] == "00"
    rate_limit_log = next(
        kwargs for event, kwargs in info_calls if event == "KRA API rate limit headers"
    )
    assert rate_limit_log["rate_limit_limit"] == "100"
    assert rate_limit_log["rate_limit_remaining"] == "42"
    assert rate_limit_log["rate_limit_reset"] == "1700000000"

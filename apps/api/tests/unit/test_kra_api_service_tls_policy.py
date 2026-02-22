import pytest

from config import Settings
from infrastructure.kra_api import client as kra_client_module


class _DummyResponse:
    text = "<response></response>"

    def raise_for_status(self):
        return None

    def json(self):
        return {"response": {"header": {"resultCode": "00"}}}


class _CaptureAsyncClient:
    captured_verify: list[bool] = []
    captured_params: list[dict | None] = []

    def __init__(self, *args, **kwargs):
        self.__class__.captured_verify.append(kwargs.get("verify"))

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, params=None):
        self.__class__.captured_params.append(
            dict(params) if params is not None else None
        )
        return _DummyResponse()


async def _run_request_and_get_verify(monkeypatch) -> bool:
    _CaptureAsyncClient.captured_verify.clear()
    _CaptureAsyncClient.captured_params.clear()
    monkeypatch.setattr(kra_client_module.httpx, "AsyncClient", _CaptureAsyncClient)

    client = kra_client_module.KRAApiClient()
    client.max_retries = 1

    await client._make_request("/TLS_TEST", {})
    return _CaptureAsyncClient.captured_verify[-1]


async def _run_request_and_get_params(monkeypatch) -> dict:
    _CaptureAsyncClient.captured_verify.clear()
    _CaptureAsyncClient.captured_params.clear()
    monkeypatch.setattr(kra_client_module.httpx, "AsyncClient", _CaptureAsyncClient)

    client = kra_client_module.KRAApiClient()
    client.max_retries = 1

    await client._make_request("/TLS_TEST", {})
    params = _CaptureAsyncClient.captured_params[-1]
    return params if params is not None else {}


@pytest.mark.asyncio
@pytest.mark.unit
async def test_async_client_uses_verify_true_by_default(monkeypatch):
    monkeypatch.delenv("KRA_API_VERIFY_TLS", raising=False)
    monkeypatch.setattr(
        kra_client_module,
        "settings",
        Settings(environment="development"),
    )

    verify = await _run_request_and_get_verify(monkeypatch)
    assert verify is True


@pytest.mark.asyncio
@pytest.mark.unit
async def test_async_client_uses_verify_false_when_flag_disabled(monkeypatch):
    monkeypatch.setenv("KRA_API_VERIFY_TLS", "false")
    monkeypatch.setattr(
        kra_client_module,
        "settings",
        Settings(environment="development"),
    )

    verify = await _run_request_and_get_verify(monkeypatch)
    assert verify is False


@pytest.mark.asyncio
@pytest.mark.unit
async def test_make_request_omits_service_key_param_when_api_key_missing(monkeypatch):
    monkeypatch.delenv("KRA_API_KEY", raising=False)
    monkeypatch.setattr(
        kra_client_module,
        "settings",
        Settings(environment="development"),
    )

    params = await _run_request_and_get_params(monkeypatch)
    assert "serviceKey" not in params

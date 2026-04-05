import pytest

from config import Settings
from infrastructure.kra_api import client as kra_client_module


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


@pytest.mark.unit
@pytest.mark.asyncio
async def test_kra_api_client_uses_configured_ssl_verification(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"response": {"header": {"resultCode": "00"}}}

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def request(self, method, url, params=None, json=None):
            captured["url"] = url
            captured["params"] = params
            return FakeResponse()

    monkeypatch.setattr(kra_client_module.settings, "kra_api_verify_ssl", False)
    monkeypatch.setattr(kra_client_module.settings, "kra_api_key", "test-api-key")
    monkeypatch.setattr(kra_client_module.httpx, "AsyncClient", FakeAsyncClient)

    client = kra_client_module.KRAApiClient()
    await client._make_request("/test-endpoint", {})

    assert client.verify_ssl is False
    assert captured["verify"] is False
    assert captured["params"]["serviceKey"] == "test-api-key"
    assert captured["params"]["_type"] == "json"

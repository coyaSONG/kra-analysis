import httpx
import pytest

from services.kra_api_service import KRAAPIError, KRAAPIService


class DummyResponse:
    def __init__(self, json_data, status_code=200, url="https://example.test/"):
        self._json = json_data
        self.status_code = status_code
        self.request = httpx.Request("GET", url)
        self._resp = httpx.Response(status_code, request=self.request, text="")

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "error", request=self.request, response=self._resp
            )


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_race_info_success(monkeypatch):
    svc = KRAAPIService()

    async def fake_request(method, url, params=None, json=None):
        assert "API214_1" in url
        payload = {
            "response": {
                "header": {"resultCode": "00", "resultMsg": "OK"},
                "body": {"items": {"item": [{"rcDate": "20240719", "rcNo": 1}]}},
            }
        }
        return DummyResponse(payload)

    monkeypatch.setattr(svc.client, "request", fake_request)

    result = await svc.get_race_info("20240719", "1", 1, use_cache=False)
    assert result["response"]["header"]["resultCode"] == "00"


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_race_info_http_error(monkeypatch):
    svc = KRAAPIService()

    async def fake_request(method, url, params=None, json=None):
        return DummyResponse({}, status_code=400)

    monkeypatch.setattr(svc.client, "request", fake_request)

    # Tenacity wraps repeated failures into RetryError
    import tenacity

    with pytest.raises(tenacity.RetryError):
        await svc.get_race_info("20240719", "1", 1, use_cache=False)


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_race_info_connection_error(monkeypatch):
    svc = KRAAPIService()

    async def fake_request(method, url, params=None, json=None):
        raise httpx.HTTPError("boom")

    monkeypatch.setattr(svc.client, "request", fake_request)

    import tenacity

    with pytest.raises(tenacity.RetryError):
        await svc.get_race_info("20240719", "1", 1, use_cache=False)


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_jockey_and_trainer_success(monkeypatch):
    svc = KRAAPIService()

    async def fake_request(method, url, params=None, json=None):
        if "API12_1" in url:
            payload = {
                "response": {
                    "header": {"resultCode": "00", "resultMsg": "OK"},
                    "body": {"items": {"item": {"jkName": "홍길동", "jkNo": "080405"}}},
                }
            }
        else:
            payload = {
                "response": {
                    "header": {"resultCode": "00", "resultMsg": "OK"},
                    "body": {"items": {"item": {"trName": "안우성", "trNo": "070180"}}},
                }
            }
        return DummyResponse(payload)

    monkeypatch.setattr(svc.client, "request", fake_request)

    jockey = await svc.get_jockey_info("080405", use_cache=False)
    assert jockey["response"]["header"]["resultCode"] == "00"

    trainer = await svc.get_trainer_info("070180", use_cache=False)
    assert trainer["response"]["header"]["resultCode"] == "00"


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.asyncio
async def test_batch_get_race_results(monkeypatch):
    svc = KRAAPIService()

    async def fake_get(race_date, meet, race_no, use_cache=True):
        if race_no == 2:
            raise KRAAPIError("fail race 2")
        return {"ok": True, "race_no": race_no}

    monkeypatch.setattr(svc, "get_race_result", fake_get)

    out = await svc.batch_get_race_results("20240719", "1", [1, 2, 3])
    assert out[1]["ok"] is True
    assert out[2] is None  # error path handled
    assert out[3]["race_no"] == 3
